import hashlib
import importlib.util
import json
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('podcut_install', Path(__file__).resolve().parents[1] / 'scripts' / 'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def reject_run(args):
    raise AssertionError('Installation was not expected: ' + repr(args))


def test_healthy_tools_are_reused(monkeypatch):
    monkeypatch.setattr(installer, 'usable_tool', lambda name: '/tools/' + name)
    monkeypatch.setattr(installer, 'run', reject_run)
    assert installer.ensure_media() == {'ffmpeg': '/tools/ffmpeg', 'ffprobe': '/tools/ffprobe'}


def test_check_is_read_only_when_everything_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(installer, 'usable_tool', lambda name: None)
    monkeypatch.setattr(installer, 'run', reject_run)
    (tmp_path / 'pyproject.toml').write_text('[project]', encoding='utf-8')
    assert not any(installer.ensure_media(check=True).values())
    result = installer.ensure_python_dependencies(check=True, root=tmp_path)
    assert 'faster_whisper' not in result['missing_modules']
    assert 'sherpa_onnx' in result['missing_modules']
    assert not (tmp_path / '.venv').exists()


def test_partial_ffmpeg_is_not_blindly_reinstalled(monkeypatch):
    monkeypatch.setattr(installer, 'usable_tool', lambda name: '/tools/ffmpeg' if name == 'ffmpeg' else None)
    monkeypatch.setattr(installer, 'run', reject_run)
    monkeypatch.delenv('PODCUT_FFPROBE', raising=False)
    with pytest.raises(RuntimeError, match='Only part'):
        installer.ensure_media()


def test_install_failure_cannot_be_reported_as_success(monkeypatch):
    monkeypatch.setattr(installer, 'usable_tool', lambda name: None)
    monkeypatch.setattr(installer, 'run', lambda args: None)
    monkeypatch.setattr(installer, 'media_install_command', lambda: ['package-manager', 'install'])
    monkeypatch.setattr(installer, 'refresh_windows_path', lambda: None)
    monkeypatch.delenv('PODCUT_FFMPEG', raising=False)
    monkeypatch.delenv('PODCUT_FFPROBE', raising=False)
    with pytest.raises(RuntimeError, match='did not produce a usable'):
        installer.ensure_media()


@pytest.mark.parametrize('system,available,expected', [
    ('Windows', {'winget'}, ['winget', 'install', '--id', 'Gyan.FFmpeg', '--exact']),
    ('Darwin', {'brew'}, ['brew', 'install', 'ffmpeg']),
    ('Linux', {'sudo', 'apt-get'}, ['sudo', 'apt-get', 'install', '-y', 'ffmpeg']),
])
def test_platform_package_manager_selection(system, available, expected):
    command = installer.media_install_command(system, lambda name: name if name in available else None, is_root=False)
    assert command[:len(expected)] == expected
    assert '--force' not in command


def test_no_manager_does_not_invent_an_installation_route():
    with pytest.raises(RuntimeError, match='No supported available package manager'):
        installer.media_install_command('Linux', lambda name: None, is_root=False)


def test_repeated_setup_skips_working_environment(tmp_path, monkeypatch):
    definition = tmp_path / 'pyproject.toml'
    definition.write_text('[project]', encoding='utf-8')
    python = installer.environment_python(tmp_path)
    python.parent.mkdir(parents=True)
    python.write_text('fixture', encoding='utf-8')
    marker = tmp_path / '.venv' / 'podcut-install.json'
    marker.write_text(json.dumps({'project_hash': hashlib.sha256(definition.read_bytes()).hexdigest(),
                                  'transcription': True}), encoding='utf-8')
    monkeypatch.setattr(installer, 'check_modules', lambda python, transcribe, with_whisper=False: [])
    monkeypatch.setattr(installer, 'run', reject_run)
    assert installer.ensure_python_dependencies(root=tmp_path)['installer_configuration_current']


def test_premiere_flag_does_not_claim_an_app_connection(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(installer, 'ensure_media', lambda check: {'ffmpeg': '/ffmpeg', 'ffprobe': '/ffprobe'})
    monkeypatch.setattr(installer, 'ensure_python_dependencies', lambda *args, **kwargs: {'missing_modules': []})
    assert installer.main(['--check', '--premiere']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['local_tools_ready']
    assert result['premiere']['connection_verified'] is False


def test_whisper_is_only_required_when_requested(tmp_path):
    python = tmp_path / 'missing-python'
    assert 'yt_dlp' not in installer.check_modules(python, True)
    assert 'yt_dlp' in installer.check_modules(python, True, with_archive=True)
    assert 'faster_whisper' not in installer.check_modules(python, True)
    assert 'faster_whisper' in installer.check_modules(python, True, with_whisper=True)


def test_conflicting_transcription_install_options_fail_before_install(monkeypatch):
    monkeypatch.setattr(installer, 'ensure_media', lambda *a: pytest.fail('Should reject before installation'))
    with pytest.raises(SystemExit):
        installer.main(['--without-transcription', '--with-whisper'])


def test_archive_node_check_does_not_install(monkeypatch):
    monkeypatch.setattr(installer, 'usable_node', lambda: None)
    monkeypatch.setattr(installer, 'run', reject_run)
    assert installer.ensure_node(check=True) is None


def test_working_archive_node_is_reused(monkeypatch):
    monkeypatch.setattr(installer, 'usable_node', lambda: '/runtime/node')
    monkeypatch.setattr(installer, 'run', reject_run)
    assert installer.ensure_node() == '/runtime/node'


def test_incompatible_node_is_not_silently_overwritten(monkeypatch):
    monkeypatch.setattr(installer, 'usable_node', lambda: None)
    monkeypatch.setenv('CREATOR_FLOW_NODE', '/old/node')
    monkeypatch.setattr(installer, 'run', reject_run)
    with pytest.raises(RuntimeError, match='was not overwritten'):
        installer.ensure_node()
