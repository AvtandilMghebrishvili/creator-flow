"""Local bootstrap using only Python's standard library. Never installs Premiere itself."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULES = ['numpy', 'scipy', 'soundfile', 'PIL', 'fontTools', 'podcut']


def run(args):
    print('Running: ' + ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), check=True, cwd=ROOT)


def usable_tool(name):
    path = os.environ.get('PODCUT_' + name.upper()) or shutil.which(name)
    if not path:
        return None
    try:
        result = subprocess.run([path, '-version'], capture_output=True, timeout=20)
        return path if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def media_install_command(system=None, which=None, is_root=None):
    system = system or platform.system()
    which = which or shutil.which
    if system == 'Windows' and which('winget'):
        return [which('winget'), 'install', '--id', 'Gyan.FFmpeg', '--exact', '--source', 'winget',
                '--no-upgrade', '--accept-source-agreements', '--accept-package-agreements']
    if system == 'Darwin' and which('brew'):
        return [which('brew'), 'install', 'ffmpeg']
    if system == 'Linux':
        if is_root is None:
            is_root = os.geteuid() == 0
        prefix = [] if is_root else [which('sudo')] if which('sudo') else None
        if prefix is not None:
            if which('apt-get'):
                return prefix + [which('apt-get'), 'install', '-y', 'ffmpeg']
            if which('dnf'):
                return prefix + [which('dnf'), 'install', '-y', 'ffmpeg']
    raise RuntimeError('No supported available package manager. The agent must install FFmpeg/ffprobe '
                       'from the official download links in docs/SETUP.md, then rerun. No system changes made here.')


def refresh_windows_path():
    if platform.system() != 'Windows':
        return
    import winreg
    paths = [os.environ.get('PATH', '')]
    for hive, key in [(winreg.HKEY_CURRENT_USER, 'Environment'),
                      (winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment')]:
        try:
            with winreg.OpenKey(hive, key) as handle:
                paths.append(os.path.expandvars(winreg.QueryValueEx(handle, 'Path')[0]))
        except OSError:
            pass
    local = os.environ.get('LOCALAPPDATA')
    if local:
        paths.append(str(Path(local) / 'Microsoft' / 'WinGet' / 'Links'))
    os.environ['PATH'] = os.pathsep.join(paths)


def ensure_media(check=False):
    found = {name: usable_tool(name) for name in ['ffmpeg', 'ffprobe']}
    if all(found.values()) or check:
        return found
    # Do not replace custom/broken executable overrides or repeatedly reinstall an existing build.
    if any(os.environ.get('PODCUT_' + name.upper()) for name, value in found.items() if not value):
        raise RuntimeError('A configured PODCUT_FFMPEG/PODCUT_FFPROBE is unusable. Repair that path first.')
    if any(found.values()):
        raise RuntimeError('Only part of FFmpeg works. Locate the matching ffmpeg/ffprobe pair or repair PATH; '
                           'the agent should not install a second conflicting copy.')
    run(media_install_command())
    refresh_windows_path()
    found = {name: usable_tool(name) for name in ['ffmpeg', 'ffprobe']}
    if not all(found.values()):
        raise RuntimeError('Installation did not produce a usable FFmpeg/ffprobe pair in this session. '
                           'Inspect the package result and PATH; do not claim setup succeeded.')
    return found


def environment_python(root=ROOT):
    return root / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def check_modules(python, transcribe, with_whisper=False, with_archive=False):
    names = MODULES + (['sherpa_onnx', 'huggingface_hub'] if transcribe else [])
    if with_whisper:
        names.append('faster_whisper')
    if with_archive:
        names.extend(['yt_dlp', 'yt_dlp_ejs'])
    if not python.is_file():
        return names
    code = '''import importlib,json,sys
missing=[]
for name in json.loads(sys.argv[1]):
    try: importlib.import_module(name)
    except Exception: missing.append(name)
print(json.dumps(missing))
'''
    result = subprocess.run([str(python), '-B', '-c', code, json.dumps(names)], capture_output=True,
                            text=True, encoding='utf-8', errors='replace', timeout=120)
    if result.returncode:
        raise RuntimeError('The existing virtual environment does not run. Preserve it and let the agent '
                           'diagnose/recreate an explicitly chosen environment; it was not deleted.')
    return json.loads(result.stdout.strip().splitlines()[-1])


def ensure_python_dependencies(check=False, transcribe=True, root=ROOT, with_whisper=False, with_archive=False):
    python = environment_python(root)
    missing = check_modules(python, transcribe, with_whisper, **({'with_archive': True} if with_archive else {}))
    marker = root / '.venv' / 'podcut-install.json'
    signature = hashlib.sha256((root / 'pyproject.toml').read_bytes()).hexdigest()
    saved = json.loads(marker.read_text(encoding='utf-8')) if marker.exists() else {}
    configured = saved.get('project_hash') == signature and (not transcribe or saved.get('transcription'))
    configured = configured and (not with_whisper or saved.get('whisper'))
    configured = configured and (not with_archive or saved.get('archive'))
    if check:
        return {'python': str(python), 'missing_modules': missing, 'installer_configuration_current': bool(configured)}
    if not python.is_file():
        run([sys.executable, '-m', 'venv', root / '.venv'])
    if missing or not configured:
        # No --upgrade/--force-reinstall: pip reuses satisfying installed dependencies.
        extras = (['transcribe'] if transcribe else []) + (['whisper'] if with_whisper else []) + (['archive'] if with_archive else [])
        target = str(root) + ('[' + ','.join(extras) + ']' if extras else '')
        run([python, '-m', 'pip', 'install', '-e', target])
        run([python, '-m', 'pip', 'check'])
        missing = check_modules(python, transcribe, with_whisper, **({'with_archive': True} if with_archive else {}))
        if missing:
            raise RuntimeError('Installed modules still cannot load: ' + ', '.join(missing))
        marker.write_text(json.dumps({'project_hash': signature,
                                     'transcription': transcribe or bool(saved.get('transcription')),
                                     'whisper': with_whisper or bool(saved.get('whisper')),
                                     'archive': with_archive or bool(saved.get('archive'))}), encoding='utf-8')
    return {'python': str(python), 'missing_modules': [], 'installer_configuration_current': True}


def usable_node():
    node = os.environ.get('CREATOR_FLOW_NODE') or shutil.which('node')
    if not node:
        return None
    try:
        result = subprocess.run([node, '--version'], capture_output=True, text=True, timeout=20)
        return node if result.returncode == 0 and int(result.stdout.strip().lstrip('v').split('.')[0]) >= 22 else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def ensure_node(check=False):
    found = usable_node()
    if found or check:
        return found
    if os.environ.get('CREATOR_FLOW_NODE') or shutil.which('node'):
        raise RuntimeError('Existing Node is unusable or older than 22. Diagnose it or select a supported '
                           'Node with CREATOR_FLOW_NODE; it was not overwritten. See docs/ARCHIVE.md.')
    system = platform.system()
    if system == 'Windows' and shutil.which('winget'):
        command = [shutil.which('winget'), 'install', '--id', 'OpenJS.NodeJS.LTS', '--exact',
                   '--source', 'winget', '--no-upgrade', '--accept-source-agreements', '--accept-package-agreements']
    elif system == 'Darwin' and shutil.which('brew'):
        command = [shutil.which('brew'), 'install', 'node']
    elif system == 'Linux':
        prefix = [] if os.geteuid() == 0 else [shutil.which('sudo')] if shutil.which('sudo') else None
        manager = shutil.which('apt-get') or shutil.which('dnf')
        if prefix is None or not manager:
            raise RuntimeError('Install Node 22+ using the supported vendor route in docs/ARCHIVE.md.')
        command = prefix + [manager, 'install', '-y', 'nodejs']
    else:
        raise RuntimeError('Install Node 22+ using the supported vendor route in docs/ARCHIVE.md.')
    run(command)
    refresh_windows_path()
    found = usable_node()
    if not found:
        raise RuntimeError('Node installation did not yield a usable Node 22+. See docs/ARCHIVE.md; setup is incomplete.')
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description='Install missing Creator Flow dependencies in .venv; reuse working tools.')
    parser.add_argument('--check', action='store_true', help='Read-only check; do not install or write files.')
    parser.add_argument('--without-transcription', action='store_true', help='Omit the local ASR library when not needed.')
    parser.add_argument('--with-whisper', action='store_true', help='Also install optional Whisper comparison support.')
    parser.add_argument('--premiere', action='store_true', help='Also report the required agent-managed Premiere/MCP step.')
    parser.add_argument('--with-archive', action='store_true', help='Install/reuse Node 22+ and yt-dlp for the bundled YouTube archive tools.')
    args = parser.parse_args(argv)
    if args.without_transcription and args.with_whisper:
        parser.error('--with-whisper cannot be combined with --without-transcription')
    if sys.version_info < (3, 10) or sys.maxsize <= 2**32:
        raise RuntimeError('Use 64-bit Python 3.10+; Windows users can run Install.ps1 to locate/install it.')
    tools = ensure_media(args.check)
    packages = ensure_python_dependencies(args.check, not args.without_transcription, with_whisper=args.with_whisper, with_archive=args.with_archive)
    archive_node = ensure_node(args.check) if args.with_archive else None
    ready = all(tools.values()) and not packages['missing_modules'] and (not args.with_archive or bool(archive_node))
    report = {'local_tools_ready': ready, 'media_tools': tools, 'environment': packages,
              'speech_model': 'Meta is the default transcription engine; Whisper is optional via --with-whisper. '
                              'Reuse cached weights; run a Meta sample with --allow-download before claiming the model is ready.'}
    if args.with_archive:
        report['archive'] = {'node': archive_node, 'yt_dlp_installed': 'yt_dlp' not in packages['missing_modules']}
    if args.premiere:
        report['premiere'] = {'connection_verified': False,
                              'next': 'Agent: follow docs/PREMIERE.md. Reuse a working connection; otherwise install '
                                      'the required upstream MCP/plugin and configure this client, then verify a '
                                      'read-only app query. This installer does not install Adobe or certify its connection.'}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ready else 2


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, subprocess.SubprocessError, ValueError) as exc:
        print('Creator Flow setup: ' + str(exc), file=sys.stderr)
        raise SystemExit(2)
