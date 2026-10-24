"""Explicitly capture selected saved Obsidian graph settings for Pages sharing."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NUMERIC = {
    'centerStrength': (0, 1), 'repelStrength': (0, 64),
    'linkStrength': (0, 1), 'linkDistance': (1, 1000),
    'textFadeMultiplier': (-5, 5), 'nodeSizeMultiplier': (.1, 5),
    'lineSizeMultiplier': (.1, 5), 'scale': (.01, 10),
}
FLAGS = ('showArrow', 'showTags', 'showAttachments', 'hideUnresolved', 'showOrphans')


def validate_settings(value):
    for key, (low, high) in NUMERIC.items():
        number = value.get(key)
        if type(number) not in (int, float) or not math.isfinite(number) or not low <= number <= high:
            raise ValueError(f'{key}: {low}〜{high}の有限数が必要')
    for key in FLAGS:
        if type(value.get(key)) is not bool:
            raise ValueError(f'{key}: 真偽値が必要')
    if not isinstance(value.get('search'), str) or not isinstance(value.get('colorGroups'), list):
        raise ValueError('検索条件と色グループが必要')
    for group in value['colorGroups']:
        if not isinstance(group.get('query'), str) or type(group.get('color', {}).get('rgb')) is not int:
            raise ValueError('色グループの形式が不正')
    return value


def capture(root=ROOT):
    source = root / '.obsidian/graph.json'
    raw = source.read_bytes()
    # graph.json's top-level values are the saved standard graph settings.
    settings = json.loads(raw.decode('utf-8-sig'))
    selected = {key: settings[key] for key in (*NUMERIC, *FLAGS, 'search', 'colorGroups')}
    validate_settings(selected)
    digest = hashlib.sha256(json.dumps(selected, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    payload = dict(version=1, source='.obsidian/graph.json',
        source_saved_at=datetime.fromtimestamp(source.stat().st_mtime, timezone.utc).isoformat(),
        settings_hash=digest, options=selected)
    destination = root / 'web/graph-settings.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Shared graph settings captured; local Obsidian files are unchanged.')
    return payload


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    capture()
