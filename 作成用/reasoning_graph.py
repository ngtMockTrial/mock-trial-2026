"""Markdownを正本にしてObsidian Canvasとレビュー表を更新する。"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from pathlib import Path
from urllib.parse import quote

import yaml
from obsidian_graph import write_native_graph, check_native_graph
from setup_extended_graph import sync_pins

ROOT = Path(__file__).resolve().parents[1]
NOTE_DIR = ROOT / '検討' / 'ノート'
VIEWS = {
    '00_全体ピラミッド': None,  # すべてのノートを一つの図へ。新しいノートも自動的に含める。
}
COLORS = {'証拠':'5','準備資料':'3','供述獲得候補':'3','間接事実':'4','推認':'2','要証事実':'6','最終結論':'6','反論':'1','確認課題':'3'}
SIDE_COLORS = {'検察':'#3978b7','弁護':'#be5364','共通':'#71818b'}
KINDS = set(COLORS)
REVIEWS = {'未レビュー','検討中','採用','保留','不採用'}


def link_id(value):
    m = re.fullmatch(r'\[\[(?:検討/ノート/)?([A-Z]\d{2})(?:\|[^\]]+)?\]\]', value)
    if not m:
        raise ValueError(f'関係リンクの形式が不正: {value!r}')
    return m[1]


def refs(note, field):
    values = note['meta'].get(field, [])
    if not isinstance(values, list):
        raise ValueError(f"{note['id']}: {field}はリストで指定")
    return [link_id(v) for v in values]


def load_notes(root=ROOT):
    notes = {}
    for p in sorted((root/'検討'/'ノート').glob('*.md')):
        text = p.read_text(encoding='utf-8-sig')
        match = re.match(r'\A---\r?\n(.*?)\r?\n---\r?\n(.*)\Z', text, re.S)
        if not match:
            raise ValueError(f'プロパティがありません: {p}')
        meta = yaml.safe_load(match[1])
        if not isinstance(meta, dict):
            raise ValueError(f'プロパティは辞書で指定: {p}')
        ident = meta.get('id')
        if not re.fullmatch(r'[A-Z]\d{2}', str(ident)) or ident != p.stem or ident in notes:
            raise ValueError(f'ID重複・名前不整合: {p}')
        for field in ['title','kind','side','review','status','source_group']:
            if not meta.get(field):
                raise ValueError(f'{ident}: {field}が必要です')
        if meta['kind'] not in KINDS or meta['review'] not in REVIEWS:
            raise ValueError(f'{ident}: 種類または人の判断の値が不正')
        if meta['review'] == '採用' and (not meta.get('reviewer') or not meta.get('reviewed_on')):
            raise ValueError(f'{ident}: 人の採用にはreviewerとreviewed_onが必要')
        if not isinstance(meta['source_group'], list):
            raise ValueError(f'{ident}: source_groupはリストで指定')
        notes[ident] = dict(id=ident, meta=meta, body=match[2], path=p)
    if not notes:
        raise ValueError('検討ノートがありません')
    for note in notes.values():
        for field in ['inputs','challenges','checks','answered_objections','preparation','potential_supports']:
            for ident in refs(note,field):
                if ident not in notes:
                    raise ValueError(f"{note['id']}: 存在しない{field} {ident}")
        for target in re.findall(r'\]\(([^)\n]+)\)', note['body']):
            if re.match(r'^[a-z]+:', target):
                continue
            target = target.split('#')[0]
            if target and not (note['path'].parent/target).resolve().is_file():
                raise ValueError(f"{note['id']}: 切れた原資料リンク {target}")
    # 正の支持関係だけを検査。反論の往復を論証の循環と誤判定しない。
    active, done = set(), set()
    def visit(ident):
        if ident in active:
            raise ValueError(f'支持関係が循環しています: {ident}')
        if ident in done:
            return
        active.add(ident)
        for parent in refs(notes[ident],'inputs'):
            visit(parent)
        active.remove(ident)
        done.add(ident)
    for ident in notes:
        visit(ident)
    return notes


def closure(notes, ident):
    found = set()
    def visit(n):
        if n in found:
            return
        found.add(n)
        for parent in refs(notes[n],'inputs'):
            visit(parent)
    visit(ident)
    return found


def gate(notes, target):
    if target not in notes:
        raise ValueError(f'不明な対象: {target}')
    scope = closure(notes,target)
    reasons = []
    if notes[target]['meta']['kind'] in {'推認','要証事実','最終結論','間接事実'} and not any(notes[n]['meta']['kind']=='証拠' for n in scope):
        reasons.append(f'{target}: 証拠への支持経路がない')
    for ident in sorted(scope):
        m = notes[ident]['meta']
        if m['review'] != '採用':
            reasons.append(f'{ident}: 人の判断={m["review"]}')
        if m['kind'] == '証拠' and m['status'] not in {'採用済み','法廷確認済み'}:
            reasons.append(f'{ident}: 証拠状態={m["status"]}')
        elif m['status'] in {'法廷未確認','採否留保','確認待ち','未獲得'}:
            reasons.append(f'{ident}: 前提の状態={m["status"]}')
        if m['kind'] in {'準備資料','供述獲得候補'}:
            reasons.append(f'{ident}: {m["kind"]}を現在の証拠として直接利用できない')
        if m['status'] == '法廷確認済み':
            record = m.get('court_record','')
            if not record or not (ROOT/record).is_file():
                reasons.append(f'{ident}: 法廷供述の記録ファイルがない')
        answered = refs(notes[ident],'answered_objections')
        for oid, other in notes.items():
            if ident in refs(other,'challenges') and other['meta']['review'] != '不採用' and oid not in answered:
                reasons.append(f'{ident}: {oid}への応答確認が未了')
        if answered:
            response = notes[ident]['body'].split('## 反論への応答\n',1)
            content = response[1].split('\n## ',1)[0].strip() if len(response)==2 else ''
            if not content or content.startswith('未記入') or any(oid not in content for oid in answered):
                reasons.append(f'{ident}: 応答済みの反論IDと応答本文を記録する必要がある')
    return sorted(set(reasons))


def positions(notes, ids):
    # ピラミッドを下から上へ読む。反論・質問は左右に分離。
    depth_cache = {}
    def depth(ident):
        if ident not in depth_cache:
            parents = refs(notes[ident],'inputs')
            depth_cache[ident] = max((depth(p)+1 for p in parents),default=0)
        return depth_cache[ident]
    levels = {}
    side = {'反論': [],'確認課題': [],'準備資料': [],'供述獲得候補': []}
    core_ids=[n for n in ids if notes[n]['meta']['kind'] not in {*side,'最終結論'}]
    fact_level=max((depth(n) for n in core_ids),default=1)
    def display_level(ident):
        kind=notes[ident]['meta']['kind']
        if kind=='最終結論':
            return fact_level+1
        if kind=='要証事実':
            return fact_level
        return depth(ident)
    for ident in ids:
        k=notes[ident]['meta']['kind']
        if k in side:
            side[k].append(ident)
        else:
            levels.setdefault(display_level(ident),[]).append(ident)
    loc = {}
    max_width = max((len(v) for v in levels.values()),default=1)*500
    for level, members in levels.items():
        for i,ident in enumerate(members):
            loc[ident] = ((i-(len(members)-1)/2)*500, -level*410)
    side_rows=max(1,fact_level+1)
    for i, ident in enumerate(side['反論']):
        loc[ident] = (-max_width/2-630-(i//side_rows)*500, -(i%side_rows)*410)
    for i, ident in enumerate(side['確認課題']):
        loc[ident] = (max_width/2+250+(i//side_rows)*500, -(i%side_rows)*410)
    for kind,y in [('準備資料',520),('供述獲得候補',1040)]:
        for i,ident in enumerate(side[kind]):
            loc[ident]=((i-(len(side[kind])-1)/2)*500,y)
    return {k:(int(x),int(y)) for k,(x,y) in loc.items()}


def availability(notes, ident):
    """立場と利用状態は別軸。候補の矢印は正の支持に数えない。"""
    m=notes[ident]['meta']
    if m['kind']=='準備資料':
        return 'pending','現時点は根拠に不可・採否留保調書'
    if m['kind']=='供述獲得候補':
        return 'candidate','供述の獲得候補・まだ証拠ではない'
    if m['kind']=='確認課題':
        return 'question','確認作業・回答は未記録'
    waiting=[n for n in closure(notes,ident) if notes[n]['meta']['status'] in {'採否留保','法廷未確認','未獲得'} or notes[n]['meta']['kind'] in {'準備資料','供述獲得候補'}]
    if waiting:
        return 'conditional','条件付き・未確認の前提あり：'+','.join(sorted(waiting))
    if m['kind']=='証拠':
        if m['status']=='法廷確認済み':
            return 'available','法廷確認済み・記録の内容を確認'
        if m['status']=='採用済み':
            return 'available','採用済み資料・記載の範囲で利用'
        return 'pending','現時点の利用状態を確認'
    return 'analysis','検討対象・証明済みを意味しない'


def canvas_data(notes, ids):
    loc = positions(notes,ids)
    top=min(y for x,y in loc.values())
    nodes=[];edges=[]
    categories={
        'prosecution':('検察側の主張・推認（青）',lambda m:m['side']=='検察','#3978b7'),
        'defense':('弁護側の反論・別の説明（赤）',lambda m:m['side']=='弁護','#be5364'),
        'shared':('双方共通：資料・事実命題（利用状態は札で区別）',lambda m:m['side']=='共通' and m['kind'] in {'証拠','間接事実'},'#71818b'),
        'pending':('準備専用：現時点では認定根拠にできない調書（黄）',lambda m:m['kind']=='準備資料','#b98a20'),
        'candidate':('尋問・被告人質問で獲得を目指す供述（未獲得）',lambda m:m['kind']=='供述獲得候補','#b98a20'),
        'questions':('双方の確認課題',lambda m:m['kind']=='確認課題','#71818b'),
    }
    for key,(label,predicate,color) in categories.items():
        members=[n for n in ids if predicate(notes[n]['meta'])]
        if not members:continue
        x=min(loc[n][0] for n in members)-45;y=min(loc[n][1] for n in members)-110
        right=max(loc[n][0]+420 for n in members)+45;bottom=max(loc[n][1]+300 for n in members)+45
        nodes.append(dict(id='group-'+key,type='group',label=label,x=x,y=y,width=right-x,height=bottom-y,color=color))
    nodes.append(dict(id='view-guide',type='text',x=-620,y=top-410,width=1240,height=290,text='## 一つの全体ピラミッド\n頂点：「被告人は有罪である」＝検察側の最終的立証目標・未認定。\n【立場】青＝検察／赤＝弁護／灰＝双方共通。\n【利用状態】緑の札＝採用済み資料／黄の札＝留保・未獲得・未確認の前提あり。\n黄の線は現時点で利用が確定していない前提。供述候補への灰線は準備関係で、支持する証拠の線ではありません。\n実際の回答を得たら、新しい供述記録ノートを作り、その範囲で前提を更新します。調書が自動的に採用されるわけではありません。'))
    for ident in ids:
        note=notes[ident];x,y=loc[ident]
        state,label=availability(notes,ident)
        color=SIDE_COLORS.get(note['meta']['side'],'#71818b')
        nodes.append(dict(id=ident,type='file',file=note['path'].relative_to(ROOT).as_posix(),subpath='#図の要点',x=x,y=y,width=420,height=300,color=color))
        badge_color='#b98a20' if state in {'pending','candidate','conditional'} else '#39825c' if state=='available' else color
        nodes.append(dict(id='badge-'+ident,type='text',x=x,y=y-84,width=420,height=78,text=f'**【{note["meta"]["side"]}｜{note["meta"]["kind"]}】**\n{label}',color=badge_color))
    for ident in ids:
        note=notes[ident]
        for field,label,color in [('inputs','支える・前提','4'),('challenges','弁護側の反論','1'),('checks','確認する','3'),('preparation','準備関係・現在の証拠ではない','#71818b'),('potential_supports','供述獲得後の候補・現在は利用不可','3')]:
            for other in refs(note,field):
                if other not in ids:
                    continue
                a,b=(other,ident) if field in {'inputs','preparation'} else (ident,other)
                edge_label=label;edge_color=color
                if field=='inputs' and availability(notes,other)[0] in {'pending','candidate','conditional'}:
                    edge_label='条件付き前提・現時点では未確認';edge_color='3'
                edges.append(dict(id=f'{field}-{a}-{b}',fromNode=a,toNode=b,fromSide='top' if field in {'inputs','preparation','potential_supports'} else 'right',toSide='bottom' if field in {'inputs','preparation','potential_supports'} else 'left',toEnd='arrow',color=edge_color,label=edge_label))
    return dict(nodes=nodes,edges=edges)


def preserve_layout(data, path, reflow=False):
    """人間が追加したカード・矢印と既存の配置を保持し、新規関係のみ追加する。"""
    if not path.exists():
        return data
    old=json.loads(path.read_text(encoding='utf-8'))
    old_nodes={n['id']:n for n in old.get('nodes',[])}
    generated_ids={n['id'] for n in data['nodes']}
    for node in data['nodes']:
        if node['id'] in old_nodes:
            prev=old_nodes[node['id']]
            for field in ([] if reflow else ['x','y','width','height','subpath']):
                if field in prev:
                    node[field]=prev[field]
    data['nodes'] += [n for n in old.get('nodes',[]) if n['id'] not in generated_ids]
    known={e['id'] for e in data['edges']}
    # 手描きの矢印は保存。生成辺の意味・接続先はノートを正本とする。
    old_edges={e['id']:e for e in old.get('edges',[])}
    for i,edge in enumerate(data['edges']):
        if edge['id'] in old_edges:
            for field in ['fromSide','toSide']:
                if field in old_edges[edge['id']]:
                    edge[field]=old_edges[edge['id']][field]
    data['edges'] += [e for e in old.get('edges',[]) if e['id'] not in known and not e['id'].startswith(('inputs-','challenges-','checks-','preparation-','potential_supports-'))]
    return data


def summary_svg(notes, data, title):
    # インストール前にも開ける静的プレビュー。編集の正本はMarkdownとCanvas。
    ns=[n for n in data['nodes'] if n['type']=='file' and n['id'] in notes]
    x0=min(n['x'] for n in ns)-80;y0=min(n['y'] for n in ns)-150
    w=max(n['x']+n['width'] for n in ns)-x0+80;h=max(n['y']+n['height'] for n in ns)-y0+80
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" viewBox="{x0} {y0} {w} {h}">', '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#64748b"/></marker></defs>',f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="#f7f7f4"/>',f'<text x="{x0+30}" y="{y0+55}" font-size="30" font-family="Meiryo,sans-serif">{html.escape(title)} — 下から上へ読む／色・カード数は証拠の強さを表さない</text>']
    byid={n['id']:n for n in ns}
    for e in data['edges']:
        if e['fromNode'] not in byid or e['toNode'] not in byid:
            continue
        a,b=byid[e['fromNode']],byid[e['toNode']]
        x1=a['x']+a['width']/2;y1=a['y'];x2=b['x']+b['width']/2;y2=b['y']+b['height']
        if e['color']!='4':
            x1=a['x']+a['width'];y1=a['y']+a['height']/2;x2=b['x'];y2=b['y']+b['height']/2
        col={'4':'#377459','1':'#af4250','3':'#8a690c'}.get(e['color'],e['color'])
        out.append(f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{col}" stroke-width="2" fill="none" marker-end="url(#arrow)"/>')
    palette={'検察':'#dce9f6','弁護':'#f4dedf','共通':'#e4e9ec'}
    for n in ns:
        m=notes[n['id']]['meta'];x,y=n['x'],n['y'];col=palette.get(m['side'],'#e4e9ec')
        out.append(f'<rect x="{x}" y="{y}" width="420" height="300" rx="12" fill="{col}" stroke="#7b858b"/>')
        title_lines=[m['title'][i:i+22] for i in range(0,len(m['title']),22)]
        state,label=availability(notes,n['id'])
        lines=[f'{n["id"]}  {m["kind"]}・{m["side"]}',*title_lines,f'資料状態：{m["status"]}',f'人の判断：{m["review"]}']
        if state in {'pending','candidate','conditional'}:lines.append('【現時点利用不可／条件付き】')
        summary=notes[n['id']]['body'].split('## 図の要点\n',1)[-1].split('\n## ',1)[0]
        summary=next((line for line in summary.splitlines() if line.strip() and not line.startswith('**')),'')
        lines += [summary[i:i+22] for i in range(0,min(len(summary),66),22)]
        for j,line in enumerate(lines):
            out.append(f'<text x="{x+18}" y="{y+32+j*28}" font-size="17" font-family="Meiryo,sans-serif">{html.escape(line)}</text>')
    return '\n'.join(out+['</svg>'])


def connection_guide(notes):
    """正本の関係を、往復できる名前付きの読書用一覧へ変換する。"""
    def link(ident):
        return f'[{ident} {notes[ident]["meta"]["title"]}](ノート/{ident}.md)'

    lines = ['# 接続を読む', '',
             '自動生成。関係の正本は各ノートのプロパティです。編集とコメントはリンク先のノートへ。', '',
             '矢印は「左のカードを、右のカードの前提として使う案」です。事実認定や証明済みを意味しません。', '',
             '## 結論から、前提を一段ずつ読む', '',
             'まずT01（犯人性）を選び、各推認の「前提」をたどります。反論と確認事項も同じ場所で読めます。', '']
    for ident in ['T00', 'T01', 'T02', 'T03']:
        if ident in notes:
            lines.append(f'- [{ident} {notes[ident]["meta"]["title"]}](#{ident})')
    lines += ['', '## 全カードの索引', '',
              'IDが分からなくても、命題の名前から選べます。各節の「接続先を読む」で次の節へ移れます。', '']
    for ident in notes:
        lines.append(f'- [{ident} {notes[ident]["meta"]["title"]}](#{ident})')
    relations = [
        ('inputs', '前提として読む', 'このカードを前提に使う先'),
        ('challenges', 'このカードが反論する先', 'このカードに向けられた反論'),
        ('checks', 'このカードで確認する対象', 'このカードについて残る確認事項'),
        ('preparation', '供述獲得の準備資料（現在の証拠支持ではない）', 'この資料を使う供述獲得の準備'),
        ('potential_supports', '供述獲得後の支持候補（現在は利用不可）', '将来支え得る供述候補（未獲得）'),
    ]
    for ident, note in notes.items():
        m = note['meta']
        lines += ['', f'## {ident}', '', f'**{m["title"]}**', '',
                  f'{m["kind"]}／{m["side"]}｜資料・命題の状態：{m["status"]}｜人の判断：{m["review"]}', '',
                  f'利用範囲：{availability(notes, ident)[1]}', '',
                  f'本文・出典・コメントを開く：{link(ident)}', '']
        for field, outgoing_label, incoming_label in relations:
            outgoing = refs(note, field)
            incoming = [other for other in notes if ident in refs(notes[other], field)]
            for label, targets in [(outgoing_label, outgoing), (incoming_label, incoming)]:
                if not targets:
                    continue
                lines += [f'### {label}', '']
                for target in targets:
                    lines.append(f'- {link(target)} — [接続先を読む](#{target})')
                lines.append('')
        if not any(ident in refs(other, field) or refs(note, field)
                   for field, _, _ in relations for other in notes.values()):
            lines += ['接続は未設定です。', '']
        lines += ['[全カードの索引へ](#全カードの索引)', '']
    return '\n'.join(lines) + '\n'


def connection_view(notes):
    """ネット接続不要の閲覧画面。正本と同じ関係・状態だけを書き出す。"""
    payload = {}
    for ident, note in notes.items():
        meta = note['meta']
        state, label = availability(notes, ident)
        section = note['body'].split('## 図の要点\n', 1)[-1].split('\n## ', 1)[0]
        summary = next((line.strip() for line in section.splitlines()
                        if line.strip() and not line.startswith(('#', '**'))), '')
        relative = note['path'].relative_to(ROOT).as_posix()
        payload[ident] = dict(id=ident, title=meta['title'], kind=meta['kind'],
            side=meta['side'], status=meta['status'], review=meta['review'],
            state=state, availability=label, summary=summary, body=note['body'],
            file=quote('ノート/'+note['path'].name),
            obsidian='obsidian://open?vault='+quote(str(ROOT), safe='')+'&file='+quote(relative, safe=''),
            **{field: refs(note, field) for field in
               ['inputs', 'challenges', 'checks', 'preparation', 'potential_supports']})
    # HTMLのscript終端や本文中のHTMLをデータとして保持する。
    data = json.dumps(dict(notes=payload), ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    template = Path(__file__).with_name('connection_view.html').read_text(encoding='utf-8')
    return template.replace('__GRAPH_DATA__', data)


def build(notes, reflow=False):
    write_native_graph(ROOT, notes, refs, availability)
    sync_pins(ROOT, notes, refs, availability, reflow=reflow)
    dest=ROOT/'検討'/'Canvas';dest.mkdir(parents=True,exist_ok=True)
    snapshots=ROOT/'検討'/'確認用プレビュー';snapshots.mkdir(exist_ok=True)
    for name,selected_ids in VIEWS.items():
        ids=list(notes) if selected_ids is None else selected_ids
        path=dest/(name+'.canvas')
        if any(ident not in notes for ident in ids):
            raise ValueError(f'{name}: 必要なノートがない')
        data=preserve_layout(canvas_data(notes,ids),path,reflow=reflow)
        # Canvasは派生だが人の配置も含む。変更前の一世代を残す。
        content=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
        if path.exists() and path.read_text(encoding='utf-8') != content:
            backups=ROOT/'作成用'/'構造化確認'/'Canvas前回';backups.mkdir(parents=True,exist_ok=True)
            (backups/path.name).write_bytes(path.read_bytes())
        path.write_text(content,encoding='utf-8')
        (snapshots/(name+'.svg')).write_text(summary_svg(notes,data,name),encoding='utf-8')
    (ROOT/'検討'/'接続を読む.md').write_text(connection_guide(notes),encoding='utf-8')
    (ROOT/'検討'/'つながりをたどる.html').write_text(connection_view(notes),encoding='utf-8')
    report=['# 人間のレビュー一覧','','[カード同士の接続を読む](接続を読む.md)','','自動生成。編集は各ノートのプロパティ・本文で行い、「検討を更新.cmd」で反映します。人の「採用」は論証案としての選択であり、裁判所の証拠採用ではありません。','','| ノート | 種類・立場 | 現時点の利用状態 | 人の判断 |','|---|---|---|---|']
    for ident,n in notes.items():
        m=n['meta'];report.append(f'| [{ident} {m["title"]}](ノート/{ident}.md) | {m["kind"]}・{m["side"]} | {m["status"]}／{availability(notes,ident)[1]} | {m["review"]} |')
    report += ['','## 要証事実の原稿化チェック','','人の採用、未採用・未確認の前提、反論への応答を機械的に確認します。論理の妥当性や法的な証明の十分性は判定しません。']
    for target in [n for n in ['T00','T01','T02','T03'] if n in notes]:
        reasons=gate(notes,target)
        report += ['',f'### {target} {notes[target]["meta"]["title"]}', '', '原稿化候補：保留' if reasons else '原稿化候補：人による最終点検へ']
        report += ['- '+r for r in reasons]
    report += ['','## 重複する情報源グループ','','同じグループのカードは同一の物・記録に由来することがあります。カード数を独立証拠の数として扱いません。']
    groups={}
    for ident,n in notes.items():
        if n['meta']['kind']=='証拠':
            for g in n['meta']['source_group']:groups.setdefault(g,[]).append(ident)
    for group,ids in groups.items():report.append(f'- {group}：'+', '.join(ids))
    (ROOT/'検討'/'レビュー一覧.md').write_text('\n'.join(report)+'\n',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='変更せず整合性だけを検査')
    parser.add_argument('--gate',help='対象IDの原稿化チェック。保留なら終了コード2')
    parser.add_argument('--reflow',action='store_true',help='配置を再計算する。手描きカードは保持し、変更前の図を保存')
    args=parser.parse_args()
    notes=load_notes()
    if args.check:
        check_native_graph(ROOT, notes, refs, availability)
    if args.gate:
        reasons=gate(notes,args.gate)
        print(json.dumps({'target':args.gate,'ready_for_human_final_review':not reasons,'blockers':reasons},ensure_ascii=False,indent=2))
        return 2 if reasons else 0
    if not args.check:
        build(notes,reflow=args.reflow)
    print(f'OK: {len(notes)}ノート／支持関係・参照先を検証'+('（読取専用）' if args.check else f'、Canvas{len(VIEWS)}件・標準グラフ用ノート・閲覧画面・一覧を更新'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
