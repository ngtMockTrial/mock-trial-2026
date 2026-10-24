"""Copy missing local Obsidian defaults. Never overwrite a participant's settings."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def setup(root=ROOT):
    source = root / '作成用' / 'obsidian初期設定'
    copied = []
    for template in sorted(source.rglob('*.json')):
        relative = template.relative_to(source)
        target = root / '.obsidian' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation also protects against a concurrent app write.
        try:
            with target.open('xb') as stream:
                stream.write(template.read_bytes())
        except FileExistsError:
            continue
        copied.append(relative.as_posix())
    print(f'Obsidian defaults copied: {len(copied)} (existing files preserved)')
    return copied


if __name__ == '__main__':
    setup()
