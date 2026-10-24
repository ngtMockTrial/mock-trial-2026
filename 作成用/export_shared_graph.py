"""Obsidian CLIで取得した座標を、共有用の1枚図にする（正本・設定は変更しない）。"""
from pathlib import Path
import json, math, sys, hashlib
try:
    import reportlab
except ImportError:
    sys.path.append(str(Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/python/Lib/site-packages'))
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from PIL import ImageFont
from reasoning_graph import load_notes, refs, availability
from obsidian_graph import native_graph_files

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output'/'共有用'
OUT.mkdir(parents=True, exist_ok=True)
RAW = ROOT/'作成用/構造化確認/共有図_ライブ座標_20261021.json'
live = json.loads(RAW.read_text(encoding='utf-8-sig').removeprefix('=> ').strip())
notes = load_notes(ROOT)
_, edges = native_graph_files(ROOT, notes, refs, availability)
nodes = {}
for n in live['nodes']:
    ident = Path(n['path']).name[:3]
    assert ident in notes and ident not in nodes
    if notes[ident]['meta']['kind'] in {'確認課題', '準備資料', '供述獲得候補'}:
        continue
    nodes[ident] = dict(n, id=ident, meta=notes[ident]['meta'], state=availability(notes, ident)[0])
edges = [e for e in edges if e['source'] in nodes and e['target'] in nodes]
assert len(nodes) == 34 and len(edges) == 41
live_edges = {(Path(e['source']).name[:3], Path(e['target']).name[:3]) for e in live['links']
              if Path(e['source']).name[:3] in nodes and Path(e['target']).name[:3] in nodes}
assert live_edges == {(e['source'], e['target']) for e in edges}

FONT = 'C:/Windows/Fonts/msgothic.ttc'
pdfmetrics.registerFont(TTFont('JP', FONT, subfontIndex=0))
font_cache = {}
def measure(s, size):
    if size not in font_cache: font_cache[size] = ImageFont.truetype(FONT, int(size))
    return font_cache[size].getlength(s)
def wrap(s, width, size):
    lines, line = [], ''
    for ch in s:
        if line and measure(line+ch, size) > width:
            lines.append(line); line = ''
        line += ch
    if line: lines.append(line)
    return lines

W, H = 3800, 3900
S = 0.46
pdf = OUT/'模擬裁判_全体関係図_20261021.pdf'
c = canvas.Canvas(str(pdf), pagesize=(W*S,H*S), pageCompression=1)
c.setTitle('模擬裁判 | 全体の関係図 | 2026-10-21')
c.setAuthor('模擬裁判・検討資料')
c.scale(S,S)
def color(v): return HexColor(v)
def rect(x,y,w,h,fill,stroke=None,r=0):
    c.setFillColor(color(fill)); c.setStrokeColor(color(stroke or fill)); c.setLineWidth(1.5)
    if r: c.roundRect(x,H-y-h,w,h,r,stroke=bool(stroke),fill=1)
    else: c.rect(x,H-y-h,w,h,stroke=bool(stroke),fill=1)
def text(x,y,s,size=26,fill='#253443'):
    c.setFillColor(color(fill)); c.setFont('JP',size); c.drawString(x,H-y-size*.83,s)
def line(x1,y1,x2,y2,fill,width=2,dash=None):
    c.setStrokeColor(color(fill)); c.setLineWidth(width); c.setDash(dash or [])
    c.line(x1,H-y1,x2,H-y2); c.setDash([])
def polygon(points,fill,stroke=None):
    p=c.beginPath();p.moveTo(points[0][0],H-points[0][1])
    for x,y in points[1:]:p.lineTo(x,H-y)
    p.close();c.setFillColor(color(fill));c.setStrokeColor(color(stroke or fill));c.drawPath(p,fill=1,stroke=bool(stroke))

rect(0,0,W,H,'#f8fafc')
text(115,90,'模擬裁判',29,'#61768a')
text(115,145,'全体の関係図',78,'#152d42')
text(115,250,'証拠から推認へ。検察の主張と弁護の反論を、同じ図でたどる。',30)
center = live.get('options', {}).get('centerStrength')
setting_label = f' / 中心力 約{center:.1f}' if isinstance(center, (float, int)) else ''
text(115,310,'Obsidian「論証の本筋」 / 34項目・41接続 / 2026年10月21日'+setting_label,27,'#61768a')
rect(115,375,W-230,152,'#eaf1f8',r=15)
text(145,397,'T00「被告人は有罪である」は検察側の最終立証目標・未認定。',31,'#183f65')
text(145,451,'点の大きさは表示上の重要度です。証拠力・有罪確率・人の採用判断を表しません。',27)

# 座標の相対位置を変えず、余白のある共有ページへ等方拡大する。
xmin=min(n['x'] for n in nodes.values());xmax=max(n['x'] for n in nodes.values())
ymin=min(n['y'] for n in nodes.values());ymax=max(n['y'] for n in nodes.values())
factor=min(2850/(xmax-xmin),2450/(ymax-ymin))
for n in nodes.values():
    n['cx']=W/2+(n['x']-(xmin+xmax)/2)*factor
    n['cy']=1980+(n['y']-(ymin+ymax)/2)*factor
    n['radius']=max(12,n['size']*1.4)

def overlap(a,b):
    return max(0,min(a[0]+a[2],b[0]+b[2])-max(a[0],b[0]))*max(0,min(a[1]+a[3],b[1]+b[3])-max(a[1],b[1]))
boxes=[]
obstacles=[(n['cx']-n['radius']-13,n['cy']-n['radius']-13,2*n['radius']+26,2*n['radius']+26) for n in nodes.values()]
for n in sorted(nodes.values(),key=lambda n:(-n['meta'].get('display_priority',2),n['id'])):
    m=n['meta']; title=m['title']; size=30 if n['id']=='T00' else 26
    lines=wrap(title,350,size)
    head=n['id']+' / '+{'間接事実':'事実命題','最終結論':'最終目標'}.get(m['kind'],m['kind'])
    badge={'available':'採用済み資料','conditional':'未確認前提あり'}.get(n['state'],'検討案')
    w=max(measure(t,size) for t in lines+[head])+32;h=30+len(lines)*(size+7)+31
    cx,cy,r=n['cx'],n['cy'],n['radius']+19
    candidates=[]
    for gap in (0,30,65,110,170):
        for x,y in [(cx-w/2,cy+r+gap),(cx-w/2,cy-r-h-gap),(cx+r+gap,cy-h/2),(cx-r-w-gap,cy-h/2),
                    (cx+r+gap,cy+r+gap),(cx-r-w-gap,cy+r+gap),(cx+r+gap,cy-r-h-gap),(cx-r-w-gap,cy-r-h-gap)]:
            b=(x,y,w,h)
            if x<100 or x+w>W-100 or y<570 or y+h>H-520:continue
            collisions=sum(overlap(b,q) for q in boxes+obstacles)
            candidates.append((collisions*1000+math.hypot(x+w/2-cx,y+h/2-cy),b))
    _,n['box']=min(candidates,key=lambda a:a[0]); boxes.append(n['box'])
    n['title_lines']=lines;n['font_size']=size;n['head']=head;n['badge']=badge

# 支持・反論・条件付き支持を別の線にする。元の矢印方向と接続数を維持。
for e in edges:
    a,b=nodes[e['source']],nodes[e['target']]
    dx,dy=b['cx']-a['cx'],b['cy']-a['cy'];d=math.hypot(dx,dy);ux,uy=dx/d,dy/d
    x1,y1=a['cx']+ux*(a['radius']+5),a['cy']+uy*(a['radius']+5)
    x2,y2=b['cx']-ux*(b['radius']+7),b['cy']-uy*(b['radius']+7)
    ink='#c66070' if e['field']=='challenges' else '#b17c21' if e['label']=='条件付き支持' else '#9aaebf'
    dash=[13,9] if e['field']=='challenges' else [4,8] if e['label']=='条件付き支持' else None
    line(x1,y1,x2,y2,ink,3,dash)
    polygon([(x2,y2),(x2-ux*16-uy*7,y2-uy*16+ux*7),(x2-ux*16+uy*7,y2-uy*16-ux*7)],ink)

for n in nodes.values():
    x,y,r=n['cx'],n['cy'],n['radius'];ink=f"#{n['color']['rgb']:06x}";kind=n['meta']['kind']
    if n['id']=='T00' or kind=='間接事実':
        c.setFillColor(color(ink));c.circle(x,H-y,r,fill=1,stroke=0)
    elif kind=='証拠':rect(x-r,y-r,r*2,r*2,ink)
    elif kind=='反論':polygon([(x,y-r*1.2),(x+r*1.1,y+r),(x-r*1.1,y+r)],ink)
    else:
        count=4 if kind=='推認' else 6
        polygon([(x+r*math.cos(-math.pi/2+i*2*math.pi/count),y+r*math.sin(-math.pi/2+i*2*math.pi/count)) for i in range(count)],ink)

for n in nodes.values():
    x,y,w,h=n['box'];cx,cy=n['cx'],n['cy'];ink=f"#{n['color']['rgb']:06x}"
    # 細い引出線はラベルの所属を示す。命題間の論証線ではない。
    tx=min(max(cx,x),x+w);ty=min(max(cy,y),y+h)
    line(cx,cy,tx,ty,ink,1.2)
    rect(x,y,w,h,'#ffffff','#d9e2eb',10)
    rect(x,y,5,h,ink,r=2)
    text(x+16,y+11,n['head'],22,ink)
    yy=y+42
    for s in n['title_lines']:
        text(x+16,yy,s,n['font_size']); yy+=n['font_size']+7
    state_ink='#8b6512' if n['state']=='conditional' else '#337347' if n['state']=='available' else '#6c7d8d'
    text(x+16,yy+1,n['badge'],20,state_ink)

rect(115,H-435,W-230,310,'#eef3f7',r=15)
for x,ink,s in [(150,'#3978b7','青＝検察'),(600,'#be5364','赤＝弁護'),(1050,'#71818b','灰＝双方共通')]:
    rect(x,H-405,23,23,ink,r=5);text(x+40,H-408,s,28)
for x,ink,dash,s in [(150,'#9aaebf',None,'実線＝支持'),(890,'#c66070',[13,9],'破線＝反論'),(1630,'#b17c21',[4,8],'点線＝条件付き支持')]:
    line(x,H-333,x+80,H-333,ink,3,dash);text(x+100,H-351,s,27)
text(150,H-290,'細い引出線＝ラベルとの対応。四角＝証拠、丸＝事実命題、菱形＝推認、三角＝反論、六角形＝要証事実。',25)
text(150,H-242,'黄の状態表示は未確認の前提への依存。準備・確認9項目は省略していますが、未確認や採否留保は解消していません。',25)
text(150,H-195,'出典・留保・反論の詳細は各IDの正本「検討/ノート/ID.md」へ。採否・人のレビュー・原資料は変更していません。',25)
text(115,H-76,'共有用スナップショット / ライブ座標の相対位置を保持し、ラベルを読みやすく配置',23,'#61768a')
c.showPage();c.save()
import fitz
with fitz.open(pdf) as doc:
    doc[0].get_pixmap(matrix=fitz.Matrix(2,2)).save(str(pdf.with_suffix('.png')))
    doc[0].get_pixmap(matrix=fitz.Matrix(.75,.75)).save(str(ROOT/'作成用/構造化確認/共有図_プレビュー.png'))

collisions=[]
for i,a in enumerate(nodes.values()):
    for b in list(nodes.values())[i+1:]:
        if overlap(a['box'],b['box']):collisions.append([a['id'],b['id']])
manifest=dict(date='2026-10-21',nodes=len(nodes),edges=len(edges),export_node_ids=sorted(nodes),label_overlaps=collisions,
              coordinate_source=str(RAW.relative_to(ROOT)),note_hashes={i:hashlib.sha256(notes[i]['path'].read_bytes()).hexdigest() for i in notes},
              source_graph=live,relations=edges)
(OUT/'全体関係図_書出し記録.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(pdf=str(pdf),nodes=len(nodes),edges=len(edges),label_overlaps=collisions),ensure_ascii=False))
if collisions: sys.exit(2)
