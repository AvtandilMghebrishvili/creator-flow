"""Register a small personal skill pointing to this checkout; no media or packages copied."""
import argparse
import json
import os
from pathlib import Path
import shutil
import uuid

ROOT = Path(__file__).resolve().parents[1]


def skills_directory(client, home=None, env=None):
    home = Path.home() if home is None else Path(home)
    env = os.environ if env is None else env
    if client == 'claude':
        return home / '.claude' / 'skills'
    if client != 'codex':
        raise ValueError('Choose codex or claude')
    current = home / '.agents' / 'skills'
    existing = [current, Path(env['CODEX_HOME']) / 'skills' if env.get('CODEX_HOME') else home / '.codex' / 'skills']
    # Reuse this skill's established location rather than creating duplicate entries.
    return next((p for p in existing if (p / 'creator-flow' / 'SKILL.md').is_file()), current)


def skill_text(repo):
    repo = Path(repo).resolve()
    required = ['START_HERE.md', '.agents/skills/creator-flow/SKILL.md', 'docs/USER_GUIDE.en.md']
    for name in required:
        if not (repo / name).is_file():
            raise ValueError(f'Incomplete checkout: missing {name}')
    location = repo.as_posix()
    return f'''---
name: creator-flow
description: Edit local podcasts and reviewed Shorts or Reels, or research a YouTube archive, with Meta transcription and optional Premiere delivery. Use for real-recording production, not unrelated coding or generated presenter videos.
---

# Creator Flow — Podcasts, Shorts & Reels

The installed checkout is `{location}`. Read `{location}/START_HERE.md` and `{location}/.agents/skills/creator-flow/SKILL.md` as the canonical workflow. Resolve their supporting files from that checkout, not from this personal skill folder. Keep the checkout in place; rerun scripts/register_skill.py if it moves.

For a user walkthrough read `{location}/docs/USER_GUIDE.ka.md` or `{location}/docs/USER_GUIDE.en.md`. For archive work use its docs/ARCHIVE.md; for reviewed clips use docs/CLIPS.md. Use the checkout's .venv executable (`Scripts/creator-flow.exe` on Windows, `bin/creator-flow` elsewhere). Do not clone a second archive toolkit.

Reuse the user's existing choices. Ask for the intended sources and propose count/duration before production. New transcription defaults to Meta Omnilingual ASR. Show the complete timed transcript for correction and confirmation before assembly. Offer captions on/off and original-file fonts/colors. Prepend the approved spoken teaser and retain its later occurrence; confirm current text, ranges, hook and applicable style. Preserve clean video and editable subtitles. Premiere-only delivery never forces a full episode render. Publishing needs the user's explicit request. These production gates do not impose episode-intake questions on coding/setup.
'''


def register(repo, directories, check=False, replace=False):
    text = skill_text(repo)
    plans = []
    for directory in directories:
        folder = Path(directory).expanduser() / 'creator-flow'
        target = folder / 'SKILL.md'
        if folder.is_symlink() or target.is_symlink():
            raise ValueError(f'Existing skill is a symlink; inspect its target before changing it: {target}')
        exists = target.is_file()
        matches = exists and target.read_text(encoding='utf-8') == text
        if exists and not matches and not replace and not check:
            raise ValueError(f'Existing skill differs: {target}. Use --replace to preserve a backup and update it.')
        plans.append((target, exists, matches))
    results = []
    for target, exists, matches in plans:
        backup = None
        if not check and not matches:
            target.parent.mkdir(parents=True, exist_ok=True)
            if exists:
                backup = target.with_name('SKILL.md.backup-' + uuid.uuid4().hex)
                shutil.copy2(target, backup)
            target.write_text(text, encoding='utf-8', newline='\n')
        results.append({'path': str(target), 'ready': matches or not check,
                        'changed': not check and not matches, 'backup': str(backup) if backup else None})
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description='Make Creator Flow discoverable outside this repository.')
    parser.add_argument('--client', choices=['codex', 'claude', 'both'], required=True)
    parser.add_argument('--skills-dir', type=Path, help='Override the personal skills directory for one client.')
    parser.add_argument('--check', action='store_true', help='Inspect without creating or changing files.')
    parser.add_argument('--replace', action='store_true', help='Back up a differing SKILL.md before updating it.')
    args = parser.parse_args(argv)
    if args.client == 'both' and args.skills_dir:
        parser.error('--skills-dir requires a single client')
    clients = ['codex', 'claude'] if args.client == 'both' else [args.client]
    try:
        results = register(ROOT, [args.skills_dir or skills_directory(c) for c in clients], args.check, args.replace)
    except (ValueError, OSError) as exc:
        parser.exit(2, str(exc) + '\n')
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(row['ready'] for row in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
