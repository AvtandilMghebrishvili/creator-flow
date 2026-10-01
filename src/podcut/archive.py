"""Launch the bundled archive tools without a second checkout or shell interpolation."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

COMMANDS = {
    'doctor': 'doctor.js',
    'channel-stats': 'channel-stats.js',
    'fetch-transcripts': 'fetch-transcripts.js',
    'find-candidates': 'find-candidates.js',
    'inspect': 'inspect.js',
    'legacy-render': 'render-short.js',
}


def run(tool, args):
    if tool not in COMMANDS:
        raise ValueError('Unknown archive tool')
    node = os.environ.get('CREATOR_FLOW_NODE') or shutil.which('node')
    if not node:
        raise RuntimeError('Archive tools need Node 22+. Run Install.ps1 -WithArchive '
                           'or python scripts/install.py --with-archive; see docs/ARCHIVE.md.')
    script = Path(__file__).with_name('youtube') / COMMANDS[tool]
    if not script.is_file():
        raise RuntimeError('Bundled archive script is missing. Reinstall Creator Flow.')
    env = os.environ.copy()
    # The bootstrap installs yt-dlp beside this Python. Preserve explicit/portable choices.
    data_root = Path(env.get('CREATOR_FLOW_ROOT') or env.get('YTC_ROOT') or Path.cwd())
    executable = 'yt-dlp.exe' if os.name == 'nt' else 'yt-dlp'
    bundled_ytdlp = data_root / 'tools' / executable
    environment_ytdlp = Path(sys.executable).parent / executable
    if not bundled_ytdlp.is_file() and environment_ytdlp.is_file():
        env.setdefault('CREATOR_FLOW_YTDLP', str(environment_ytdlp))
    for name in ('ffmpeg', 'ffprobe'):
        # Absolute paths also support yt-dlp's --ffmpeg-location on legacy imports.
        if not (data_root / 'tools' / 'ffmpeg' / 'bin' / (name + ('.exe' if os.name == 'nt' else ''))).is_file():
            found = shutil.which(name)
            if found:
                env.setdefault('PODCUT_' + name.upper(), found)
    if tool == 'legacy-render':
        print('Legacy renderer: no approval state or repeated spoken teaser. '
              'Use clips-review / clips-approve / clips-render for the current workflow.', file=sys.stderr)
    try:
        return subprocess.run([node, str(script), *args], env=env, check=False).returncode
    except OSError as exc:
        raise RuntimeError(f'Archive runtime could not start: {exc}') from exc
