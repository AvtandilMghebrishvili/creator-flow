"""Package only allowlisted public extension assets; never local provider state."""
import argparse
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ['manifest.json', 'core.js', 'extract.js', 'panel.js', 'background.js', 'settings.html', 'settings.js', 'settings.css', 'icons/16.png', 'icons/32.png', 'icons/128.png']


def package(output):
    folder = ROOT / 'extensions' / 'creator-flow'
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    if manifest['manifest_version'] != 3:
        raise ValueError('Expected Manifest V3.')
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        for name in ASSETS:
            archive.write(folder / name, name)
        archive.write(ROOT / 'LICENSE', 'LICENSE')
        archive.write(ROOT / 'docs' / 'STUDIO.md', 'STUDIO.md')
        archive.write(ROOT / 'docs' / 'STUDIO.ka.md', 'STUDIO.ka.md')
        archive.write(ROOT / 'docs' / 'EXTENSION.ka.md', 'README.ka.md')
        archive.write(ROOT / 'docs' / 'EXTENSION.md', 'README.en.md')
        archive.write(ROOT / 'docs' / 'EXTENSION.md', 'EXTENSION.md')
        archive.write(ROOT / 'docs' / 'EXTENSION.ka.md', 'EXTENSION.ka.md')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='dist/creator-flow-extension.zip')
    print(package(parser.parse_args().output))
