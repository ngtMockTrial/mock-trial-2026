"""Read-only repository checks for local use and CI. No Obsidian or network required."""
from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def check_originals(root=ROOT):
    ledger = root / 'docs/原文/原資料ハッシュ一覧.md'
    entries = re.findall(r'\| \[[^\]]+\]\(([^)]+)\) \| `([0-9a-f]{64})` \|',
                         ledger.read_text(encoding='utf-8'))
    if len(entries) < 15:
        raise ValueError('原資料ハッシュ台帳が不足しています（最低15件）')
    expected = set()
    for relative, digest in entries:
        path = (ledger.parent / unquote(relative)).resolve()
        if not path.is_relative_to((root / '00_元資料').resolve()):
            raise ValueError('原資料台帳に範囲外のパスがあります')
        expected.add(path)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f'原資料が欠落または変更されています: {relative}')
    actual = {p.resolve() for p in (root / '00_元資料').rglob('*') if p.is_file()}
    if expected != actual:
        raise ValueError('原資料とハッシュ台帳の登録が一致しません。追加資料を確認してください')
    return len(entries)


def check_links(root=ROOT):
    # Active documentation only: historical archives, source extracts and agent examples
    # are not interpreted as current instructions. This does not validate page anchors.
    files = list((root / 'docs').glob('*.md')) + list((root / '検討/ノート').glob('*.md'))
    files += [root / name for name in ['README.md', 'AGENTS.md', 'CLAUDE.md']]
    if (root / 'CONTRIBUTING.md').exists():
        files.append(root / 'CONTRIBUTING.md')
    files += list((root / 'docs/外部参考').glob('*.md'))
    broken = []
    for path in files:
        text = path.read_text(encoding='utf-8-sig')
        text = re.sub(r'^```.*?^```[^\n]*', '', text, flags=re.M | re.S)
        for target in re.findall(r'!?\[[^\]\n]*\]\(([^)\n]+)\)', text):
            target = target.strip().strip('<>').split('#', 1)[0]
            if not target or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target):
                continue
            if not (path.parent / unquote(target)).exists():
                broken.append(f'{path.relative_to(root)}: {target}')
    if broken:
        raise ValueError('ローカルリンク切れ:\n' + '\n'.join(broken))
    return len(files)


def run_checks(root=ROOT):
    import reasoning_graph as graph
    notes = graph.load_notes(root)
    # Run graph checks with the same root used for the repository.
    graph.check_native_graph(root, notes, graph.refs, graph.availability)
    for relative, expected in [
        ('検討/接続を読む.md', graph.connection_guide(notes)),
        ('検討/つながりをたどる.html', graph.connection_view(notes)),
    ]:
        if (root / relative).read_text(encoding='utf-8') != expected:
            raise ValueError(f'派生表示が未更新です: {relative}')
    import json
    canvas = root / '検討/Canvas/00_全体ピラミッド.canvas'
    expected = graph.preserve_layout(graph.canvas_data(notes, list(notes)), canvas)
    if json.loads(canvas.read_text(encoding='utf-8')) != expected:
        raise ValueError('Canvasの生成関係が未更新です（手描き・配置は保持して更新してください）')
    originals = check_originals(root)
    documents = check_links(root)
    result = subprocess.run([sys.executable, str(root / '作成用/test_reasoning_graph.py')], cwd=root)
    if result.returncode:
        raise ValueError('論証グラフの回帰テストに失敗しました')
    result = subprocess.run([sys.executable, str(root / '作成用/test_collaboration.py')], cwd=root)
    if result.returncode:
        raise ValueError('共同編集ツールのテストに失敗しました')
    # A hold is an expected content state. It is deliberately not CI failure.
    blockers = graph.gate(notes, 'T00')
    print(f'OK: {len(notes)} notes; {originals} originals; {documents} documents')
    print(f'T00: {"HOLD" if blockers else "human final review"}; {len(blockers)} blockers')
    print('Legal sufficiency and human approval are not assessed by this check.')


if __name__ == '__main__':
    try:
        run_checks()
    except (ValueError, OSError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        raise SystemExit(1)
