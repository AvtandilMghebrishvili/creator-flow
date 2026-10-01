"""Inspect tracked files only; never print file content or private token matches."""
from pathlib import Path
import subprocess
import re

root = Path(__file__).resolve().parents[1]
result = subprocess.run(['git', 'ls-files', '-z'], cwd=root, check=True, capture_output=True)
problems = []
# These reviewed generated graphics are public documentation, not episode media.
documentation_artwork = {
    'docs/assets/creator-flow-logo.png',
    'docs/assets/podcut-logo.png',
    'docs/assets/podcut-logo-dark.png',
    'docs/assets/podcut-workflow-guide.png',
}
for name in result.stdout.decode('utf-8').split('\0'):
    if not name:
        continue
    path = root / name
    if not path.is_file():
        continue
    if name in documentation_artwork:
        with path.open('rb') as image:
            signature = image.read(8)
        if signature != b'\x89PNG\r\n\x1a\n' or path.stat().st_size > 4_000_000:
            problems.append((name, 'invalid or oversized documentation PNG'))
        continue
    if path.suffix.lower() in {'.mp4','.mov','.mxf','.wav','.mp3','.flac','.m4a','.braw','.r3d','.prproj','.cube','.zip'} or path.stat().st_size > 1_000_000:
        problems.append((name, 'media, native artifact, or large file'))
    text = path.read_text(encoding='utf-8', errors='replace')
    if re.search(r'(gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{25,}|sk-[A-Za-z0-9]{30,})', text):
        problems.append((name, 'possible credential'))
    if re.search(r'[A-Z]:[\\/]+Users[\\/]+(?:User|[^ /\\<>]+)[\\/]', text):
        problems.append((name, 'personal absolute path'))
    if path.name.lower() in {'local-auth.json','localauth.json','.mcp.json','.env'}:
        problems.append((name, 'local configuration'))
for name, reason in problems:
    print(f'{name}: {reason}')
if problems:
    raise SystemExit(1)
print('Public tracked-file check passed.')
