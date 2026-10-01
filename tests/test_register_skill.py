import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('register_skill', Path(__file__).resolve().parents[1] / 'scripts/register_skill.py')
registration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(registration)


@pytest.fixture
def checkout(tmp_path):
    root = tmp_path / 'Creator ფლოუ'
    for name in ['START_HERE.md', '.agents/skills/creator-flow/SKILL.md', 'docs/USER_GUIDE.en.md']:
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('fixture', encoding='utf-8')
    return root


def test_check_never_creates_a_skill(checkout, tmp_path):
    target = tmp_path / 'personal'
    result = registration.register(checkout, [target], check=True)
    assert result[0]['ready'] is False
    assert not target.exists()


def test_registration_is_idempotent_and_points_to_full_checkout(checkout, tmp_path):
    target = tmp_path / 'personal'
    result = registration.register(checkout, [target])
    skill = Path(result[0]['path'])
    assert checkout.as_posix() in skill.read_text(encoding='utf-8')
    stamp = skill.stat().st_mtime_ns
    again = registration.register(checkout, [target])
    assert again[0]['ready'] and not again[0]['changed']
    assert skill.stat().st_mtime_ns == stamp


def test_differing_skill_requires_backup_and_preflights_all_targets(checkout, tmp_path):
    first, second = tmp_path / 'codex', tmp_path / 'claude'
    existing = second / 'creator-flow/SKILL.md'
    existing.parent.mkdir(parents=True)
    existing.write_text('custom instructions', encoding='utf-8')
    with pytest.raises(ValueError, match='--replace'):
        registration.register(checkout, [first, second])
    assert not first.exists()
    results = registration.register(checkout, [first, second], replace=True)
    assert Path(results[1]['backup']).read_text(encoding='utf-8') == 'custom instructions'


def test_incomplete_checkout_cannot_produce_broken_skill(tmp_path):
    with pytest.raises(ValueError, match='Incomplete checkout'):
        registration.register(tmp_path, [tmp_path / 'personal'])
    assert not (tmp_path / 'personal').exists()


def test_reuses_existing_codex_location(tmp_path):
    current = tmp_path / '.agents/skills'
    legacy = tmp_path / 'custom-codex/skills'
    assert registration.skills_directory('codex', tmp_path, {}) == current
    p = legacy / 'creator-flow/SKILL.md'
    p.parent.mkdir(parents=True)
    p.touch()
    assert registration.skills_directory('codex', tmp_path, {'CODEX_HOME': str(tmp_path/'custom-codex')}) == legacy
    assert registration.skills_directory('claude', tmp_path, {}) == tmp_path / '.claude/skills'
