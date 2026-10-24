"""正本を変えず、命題だけを点にした標準グラフを生成する。"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import quote

import yaml

FOLDER = '検討/グラフ表示'
OWNER = 'mock-trial-native-graph-v1'
FIELDS = ('inputs', 'challenges', 'checks', 'preparation', 'potential_supports')
NODE_SIZES = {5: 460, 4: 280, 3: 180, 2: 100, 1: 65}
LABELS = dict(inputs='支持', challenges='反論', checks='確認',
              preparation='準備のみ', potential_supports='将来候補')
STATE_NAMES = dict(available='採用資料', pending='留保', candidate='未獲得',
                   conditional='未確認前提あり', question='確認課題', analysis='検討案')
DETAIL_KINDS = {'確認課題', '準備資料', '供述獲得候補'}
MAIN_QUERY = f'path:"{FOLDER}/命題" [graph_scope:本筋]'
ALL_QUERY = f'path:"{FOLDER}/命題"'


def digest(content):
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def clean_name(value):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f\[\]#^]', '＿', value).strip().rstrip('.')


def native_graph_files(root, notes, refs, availability):
    """起点→終点の直接リンク。関係の種類はカード内の表に残す。"""
    names, states = {}, {}
    for ident, note in notes.items():
        m = note['meta']
        states[ident] = availability(notes, ident)
        state = STATE_NAMES[states[ident][0]]
        emphasis = ' ★最終立証目標★' if ident == 'T00' else ''
        names[ident] = f'{FOLDER}/命題/{clean_name(ident+emphasis+" 【"+m["side"]+"・"+m["kind"]+"・"+state+"】 "+m["title"])}'
    edges = []
    for ident, note in notes.items():
        for field in FIELDS:
            for other in refs(note, field):
                source, target = (other, ident) if field in {'inputs', 'preparation'} else (ident, other)
                label = LABELS[field]
                if field == 'inputs' and states[source][0] in {'pending', 'candidate', 'conditional'}:
                    label = '条件付き支持'
                side = notes[target if field == 'inputs' else source]['meta']['side']
                edges.append(dict(field=field, source=source, target=target,
                                  label=label, side=side))

    def document(meta, lines):
        return '---\n'+yaml.safe_dump(dict(generated_by=OWNER, **meta), allow_unicode=True, sort_keys=False)+'---\n\n'+'\n'.join(lines)+'\n'

    files = {}
    for ident, note in notes.items():
        m = note['meta']; state, description = states[ident]
        priority = m.get('display_priority', 5 if ident == 'T00' else 2)
        if type(priority) is not int or priority not in NODE_SIZES:
            raise ValueError(f'{ident}: display_priorityは1〜5の整数')
        if (ident == 'T00') != (priority == 5):
            raise ValueError('表示重要度5はT00専用です')
        short_kind = {'最終結論':'目標','間接事実':'事実命題','供述獲得候補':'供述候補','確認課題':'確認'}.get(m['kind'],m['kind'])
        prefix = '⚠ ' if state in {'pending','candidate','conditional'} else ''
        label_title = m['title'] if len(m['title']) <= 18 else m['title'][:18]+'…'
        meta = dict(graph_id=ident, side=m['side'], kind=m['kind'], availability=state,
                    graph_scope='準備・確認' if m['kind'] in DETAIL_KINDS else '本筋',
                    evidence_status=m['status'], human_review=m['review'],
                    display_priority=priority, node_size=NODE_SIZES[priority],
                    graph_label=f'{prefix}{ident}【{short_kind}】{label_title}',
                    tags=['裁判グラフ/命題', '立場/'+m['side'], '分類/'+m['kind'], '利用状態/'+state])
        if ident == 'T00':
            meta['cssclasses'] = ['mock-trial-final-goal']
        summary = note['body'].split('## 図の要点\n', 1)[-1].split('\n## ', 1)[0].strip()
        lines = [f'# {ident} {m["title"]}', '',
                 '> グラフ表示用の自動生成ノートです。編集・コメント・人のレビューは末尾の正本へ。', '',
                 f'**立場：{m["side"]}｜分類：{m["kind"]}**', '',
                 f'利用状態：{description}。資料・命題の状態：{m["status"]}。人の判断：{m["review"]}。', '',
                 summary, '', '## このカードからの接続', '',
                 '矢印はこのカード → 接続先。線だけでは関係の種類を表せません。以下の関係名で支持・反論・確認・準備・将来候補を区別します。', '']
        if ident == 'T00':
            lines[2:2] = ['> [!abstract] 最終立証目標・未認定',
                          '> **被告人は有罪である**',
                          '>', '> 検察側が最終的に証明したい命題です。人の有罪認定を記録するものではありません。', '']
        outgoing = [e for e in edges if e['source'] == ident]
        if outgoing:
            lines += ['| 関係 | 接続先 |', '|---|---|']
        # 表中の別名区切りはエスケープしないとObsidianが列区切りと解釈する。
        lines += [f'| {e["label"]} | [[{names[e["target"]]}\\|{e["target"]} {notes[e["target"]]["meta"]["title"]}]] |' for e in outgoing]
        if not outgoing:
            lines.append('このカードを起点にする接続はありません。')
        lines += ['', '## このカードに入る接続', '',
                  '前提・反論・確認事項をここから開けます。閲覧リンクはグラフに逆向きの線を追加しません。', '']
        incoming = [e for e in edges if e['target'] == ident]
        if incoming:
            lines += ['| 関係 | 接続元 |', '|---|---|']
        for e in incoming:
            url = 'obsidian://open?vault='+quote(root.name, safe='')+'&file='+quote(names[e['source']]+'.md', safe='')
            lines.append(f'| {e["label"]} | [{e["source"]} {notes[e["source"]]["meta"]["title"]}]({url}) |')
        if not incoming:
            lines.append('このカードを終点にする接続はありません。')
        lines += ['', '> 準備・将来候補は現在の証拠支持に数えません。確認課題も確認済みという意味ではありません。']
        relative = note['path'].relative_to(root).with_suffix('').as_posix()
        lines += ['', '## 正本・出典・人間のコメント', '',
                  f'[[{relative}|{ident}の編集用ノートを開く]]', '',
                  '原資料への出典は正本に記載。図示は認定済み・因果関係の成立を意味しません。', '',
                  '## 生成の記録', '', '2026-10-21：関係名の中間ノードを廃止し、直接リンクと関係表へ整理。確認・準備は通常表示から外し、本文と詳細表示に保持。正本の採否・人のレビューは変更しない。']
        files[names[ident]+'.md'] = document(meta, lines)
    return files, edges


def write_native_graph(root, notes, refs, availability):
    files, edges = native_graph_files(root, notes, refs, availability)
    ledger = root/'作成用/構造化確認/グラフ生成台帳.json'
    previous = json.loads(ledger.read_text(encoding='utf-8')) if ledger.exists() else {}
    # 人が派生ノートへ書き込んだ場合も、黙って上書き・削除しない。
    for relative in set(previous) | set(files):
        path = root/relative
        if not path.resolve().is_relative_to((root/FOLDER).resolve()):
            raise ValueError('グラフ生成先が専用フォルダ外です')
        if path.exists():
            content = path.read_text(encoding='utf-8')
            if relative not in previous or digest(content) != previous[relative]:
                raise ValueError(f'グラフ表示ノートに生成外の編集があります。正本への移し替えを確認してください: {relative}')
    for relative, content in files.items():
        path = root/relative; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
    for relative in set(previous)-set(files):
        path = root/relative
        if path.exists():
            path.unlink()
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps({p:digest(c) for p,c in files.items()}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return files, edges


def graph_options(base=None, search=None):
    options = dict(base or {})
    options.update(search=search or MAIN_QUERY, showTags=False,
                   showAttachments=False, hideUnresolved=True, showOrphans=True,
                   showArrow=True, textFadeMultiplier=.3, nodeSizeMultiplier=1.35,
                   scale=.6,
                   lineSizeMultiplier=.8, centerStrength=.5, repelStrength=10,
                   linkStrength=.85, linkDistance=140,
                   colorGroups=[dict(query='[graph_id:T00]',color=dict(a=1,rgb=0x70b7ff))]+[dict(query=f'[side:{side}]', color=dict(a=1, rgb=int(color,16)))
                                for side,color in [('検察','3978b7'),('弁護','be5364'),('共通','71818b')]],
                   **{'collapse-filter':False, 'collapse-color-groups':False})
    return options


def install_goal_style(root):
    """標準CSSスニペットだけで結論見出しを強調。プラグインを追加しない。"""
    snippets=root/'.obsidian/snippets';snippets.mkdir(parents=True,exist_ok=True)
    (snippets/'mock-trial-final-goal.css').write_text(
        Path(__file__).with_name('final-goal.css').read_text(encoding='utf-8'),encoding='utf-8')
    appearance=root/'.obsidian/appearance.json'
    settings=json.loads(appearance.read_text(encoding='utf-8')) if appearance.exists() else {}
    enabled=settings.setdefault('enabledCssSnippets',[])
    if 'mock-trial-final-goal' not in enabled:
        enabled.append('mock-trial-final-goal')
    appearance.write_text(json.dumps(settings,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def check_native_graph(root, notes, refs, availability):
    expected, edges = native_graph_files(root, notes, refs, availability)
    for relative, content in expected.items():
        path = root/relative
        if not path.exists() or path.read_text(encoding='utf-8') != content:
            raise ValueError(f'標準グラフ用ノートに未更新・編集・欠落があります: {relative}')
    actual = {p.relative_to(root).as_posix() for p in (root/FOLDER).rglob('*.md')}
    if set(expected) != actual:
        raise ValueError('標準グラフ用フォルダに未登録のノートがあります')
    for content in expected.values():
        for target in re.findall(r'\[\[([^]|]+)(?:\|[^]]+)?\]\]', content.replace('\\|', '|')):
            if not (root/(target+'.md')).is_file():
                raise ValueError(f'標準グラフに参照切れがあります: {target}')
    return len(expected), len(edges)


def configure_graph(root, notes, refs, availability):
    """初回だけ実行する設定。通常更新では人のグラフ設定を上書きしない。"""
    files, edges = write_native_graph(root, notes, refs, availability)
    config = root/'.obsidian'; config.mkdir(exist_ok=True)
    install_goal_style(root)
    backup = root/'作成用/構造化確認/グラフ設定導入前'; backup.mkdir(parents=True, exist_ok=True)
    for name in ['graph.json', 'bookmarks.json']:
        path = config/name
        if path.exists() and not (backup/name).exists():
            (backup/name).write_bytes(path.read_bytes())
    graph_path = config/'graph.json'
    base = json.loads(graph_path.read_text(encoding='utf-8')) if graph_path.exists() else {}
    options = graph_options(base)
    graph_path.write_text(json.dumps(options, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    bookmarks_path = config/'bookmarks.json'
    bookmarks = json.loads(bookmarks_path.read_text(encoding='utf-8')) if bookmarks_path.exists() else dict(items=[])
    # ブックマークの保存形式はインストール済みObsidianの実装で確認。
    items = []
    for title, query in [
        ('01 論証の本筋', MAIN_QUERY),
        ('02 詳細・準備と確認を含む', ALL_QUERY),
    ]:
        preset=graph_options(base,query)
        if not title.startswith('01 '):
            preset['showOrphans']=False
        items.append(dict(type='graph', title=title, ctime=1792512000000, options=preset))
    group = dict(type='group', title='模擬裁判・構造グラフ', ctime=1792512000000, items=items)
    matching = [item for item in bookmarks['items'] if item.get('title')==group['title'] and item.get('type')=='group']
    if matching:
        # 既存の人の追加項目は残し、同名の生成プリセットだけを更新する。
        existing = matching[0]
        titles = {item['title'] for item in items} | {'01 全体・立場で色分け', '02 支持・条件付き支持だけ', '03 反論の接続', '04 確認課題の接続', '05 準備・将来候補の接続'}
        existing['items'] = [item for item in existing.get('items',[]) if item.get('title') not in titles] + items
    else:
        bookmarks['items'].append(group)
    bookmarks_path.write_text(json.dumps(bookmarks,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    return len(notes), len(edges)
