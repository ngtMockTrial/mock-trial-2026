"""表示の重要度・型と、正本の証拠状態を分離した構造グラフ。"""
import hashlib
import json
from pathlib import Path

DATA = '検討/構造グラフ.json'
FIELDS = ('inputs', 'challenges', 'checks', 'preparation', 'potential_supports')
LABELS = dict(inputs='支持', challenges='反論', checks='確認', preparation='準備のみ', potential_supports='将来候補')
SIZES = {5: 56, 4: 42, 3: 32, 2: 23, 1: 16}


def default_priority(ident, kind):
    if ident == 'T00': return 5
    if ident in {'T01', 'D09'}: return 4
    if kind in {'要証事実', '推認', '反論'}: return 3
    return 2


def graph_payload(root, notes, refs, availability):
    nodes = []
    for ident, note in notes.items():
        m = note['meta']
        priority = m.get('display_priority', default_priority(ident, m['kind']))
        if type(priority) is not int or priority not in SIZES:
            raise ValueError(f'{ident}: display_priorityは1〜5の整数')
        if ident == 'T00' and priority != 5 or ident != 'T00' and priority == 5:
            raise ValueError('表示重要度5は最終目標T00だけに設定')
        state, description = availability(notes, ident)
        section = note['body'].split('## 図の要点\n', 1)[-1].split('\n## ', 1)[0]
        summary = '\n'.join(line for line in section.splitlines() if not line.startswith('**')).strip()
        nodes.append(dict(id=ident, title=m['title'], kind=m['kind'], side=m['side'],
                          status=m['status'], review=m['review'], priority=priority,
                          radius=SIZES[priority], state=state, availability=description,
                          sources=m['source_group'], summary=summary,
                          path=note['path'].relative_to(root).as_posix()))
    byid = {n['id']: n for n in nodes}
    edges = []
    for ident, note in notes.items():
        for field in FIELDS:
            for other in refs(note, field):
                source, target = (other, ident) if field in {'inputs','preparation'} else (ident, other)
                conditional = field == 'inputs' and byid[source]['state'] in {'pending','candidate','conditional'}
                edges.append(dict(source=source, target=target, field=field,
                                  label='条件付き支持' if conditional else LABELS[field], conditional=conditional))
    return dict(schema=2, nodes=nodes, edges=edges,
                source_hashes={n['path'].relative_to(root).as_posix(): hashlib.sha256(n['path'].read_bytes()).hexdigest() for n in notes.values()})


def write_graph(root, notes, refs, availability):
    payload = graph_payload(root, notes, refs, availability)
    (root/DATA).write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    # 同じ表示コードを単体でも検査できる。プレビューも正本ではない。
    source = Path(__file__).with_name('trial-graph')
    css = (source/'styles.css').read_text(encoding='utf-8')
    js = (source/'view.js').read_text(encoding='utf-8')
    encoded = json.dumps(payload, ensure_ascii=False).replace('<','\\u003c')
    preview = '<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>模擬裁判・構造グラフ</title><style>'+css+'</style><body><main id="graph"></main><script>'+js+'</script><script>TrialGraph.mount(document.getElementById("graph"),'+encoded+',p=>{location.href="obsidian://open?vault="+encodeURIComponent('+json.dumps(str(root),ensure_ascii=False)+')+"&file="+encodeURIComponent(p)});</script></body></html>'
    (root/'検討/構造グラフ.html').write_text(preview, encoding='utf-8')
    return payload


def check_graph(root, notes, refs, availability):
    expected = graph_payload(root, notes, refs, availability)
    if json.loads((root/DATA).read_text(encoding='utf-8')) != expected:
        raise ValueError('構造グラフが未更新です。検討を更新.cmdを実行してください')
