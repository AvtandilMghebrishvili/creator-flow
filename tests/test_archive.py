import os
from pathlib import Path
from types import SimpleNamespace
import pytest
from podcut import archive
from podcut.cli import parser, execute


def test_archive_dispatch_preserves_arguments_workspace_and_exit_status(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setenv('CREATOR_FLOW_NODE', '/runtime/node')
    monkeypatch.setenv('CREATOR_FLOW_ROOT', str(tmp_path))
    monkeypatch.setenv('CREATOR_FLOW_YTDLP', '/explicit/yt-dlp')
    monkeypatch.setattr(archive.subprocess, 'run', lambda cmd, **kw: calls.append((cmd, kw)) or SimpleNamespace(returncode=7))
    args = parser().parse_args(['archive', 'channel-stats', '--channel', 'https://example.test/@a & b'])
    with pytest.raises(SystemExit) as exc:
        execute(args)
    assert exc.value.code == 7
    cmd, kw = calls[0]
    assert cmd[-2:] == ['--channel', 'https://example.test/@a & b']
    assert Path(cmd[1]).is_file()
    assert kw['env']['CREATOR_FLOW_ROOT'] == str(tmp_path)
    assert kw['env']['CREATOR_FLOW_YTDLP'] == '/explicit/yt-dlp'
    assert 'shell' not in kw


def test_archive_reuses_environment_ytdlp_without_changing_global_env(monkeypatch, tmp_path):
    python = tmp_path / 'venv' / ('Scripts' if os.name == 'nt' else 'bin') / ('python.exe' if os.name == 'nt' else 'python')
    python.parent.mkdir(parents=True)
    ytdlp = python.with_name('yt-dlp.exe' if os.name == 'nt' else 'yt-dlp')
    ytdlp.touch()
    monkeypatch.setattr(archive.sys, 'executable', str(python))
    monkeypatch.setenv('CREATOR_FLOW_NODE', '/node')
    monkeypatch.setenv('CREATOR_FLOW_ROOT', str(tmp_path))
    monkeypatch.delenv('CREATOR_FLOW_YTDLP', raising=False)
    calls = []
    monkeypatch.setattr(archive.subprocess, 'run', lambda cmd, **kw: calls.append(kw) or SimpleNamespace(returncode=0))
    assert archive.run('doctor', []) == 0
    assert calls[0]['env']['CREATOR_FLOW_YTDLP'] == str(ytdlp)
    assert 'CREATOR_FLOW_YTDLP' not in os.environ
    portable = tmp_path / 'tools' / ytdlp.name
    portable.parent.mkdir()
    portable.touch()
    archive.run('doctor', [])
    assert 'CREATOR_FLOW_YTDLP' not in calls[1]['env']


def test_missing_node_has_actionable_error(monkeypatch):
    monkeypatch.delenv('CREATOR_FLOW_NODE', raising=False)
    monkeypatch.setattr(archive.shutil, 'which', lambda _: None)
    with pytest.raises(RuntimeError, match='WithArchive'):
        archive.run('doctor', [])


def test_cannot_launch_an_arbitrary_script():
    with pytest.raises(ValueError, match='Unknown'):
        archive.run('../../something', [])
