"""標準グラフをExtended Graphで構成。自動レイアウトは標準の物理配置を使う。"""
from __future__ import annotations
import json
from pathlib import Path

STATE_ID='mock-trial-structure-v2'


def sync_pins(root, notes, refs, availability, reflow=False):
    """自然配置には生成座標を追加しない。手動ピンも通常更新では変更しない。"""
    return


def configure(root):
    from reasoning_graph import load_notes,refs,availability
    from obsidian_graph import configure_graph,graph_options
    notes=load_notes(root)
    configure_graph(root,notes,refs,availability)
    path=root/'.obsidian/plugins/extended-graph/data.json'
    data=json.loads(path.read_text(encoding='utf-8'))
    backup=root/'作成用/構造化確認/ExtendedGraph導入前.json'
    if not backup.exists():backup.write_bytes(path.read_bytes())
    features=data['enableFeatures']['graph']
    for key in ['auto-enabled','shapes','elements-stats','names','arrows']:
        features[key]=True
    features['properties']=False
    data.update(nodesSizeProperties=['node_size'],nodesSizeFunction='constant',mockTrialLayout='organic',
                nodesSizeRange={'min':1,'max':1},nodesColorFunction='default',
                maxNodes=500,usePropertiesForName=['graph_label'],numberOfCharacters=28,
                showOnlyFileName=True,noExtension=True,addBackgroundToName=True,
                dynamicVerticalOffset=True,nameVerticalOffset=4,showNamesWhenNeighborHighlighted=True,
                showPinIcon=False,allowExternalImages=False,allowExternalLocalImages=False,
                canonicalizePropertiesWithDataview=False,startingStateID=STATE_ID,
                collapseState=True,collapseLegend=True,openInNewTab=False)
    shape_kinds={'square':['証拠'],'circle':['間接事実','接続','最終結論'],
                 'triangle':['反論'],'diamond':['推認'],'hexagon':['要証事実'],
                 'pentagon':['確認課題'],
                 'octagon':['準備資料','供述獲得候補']}
    for index,(shape,query) in enumerate(data['shapeQueries'].items()):
        query.update(index=index,combinationLogic='OR',rules=[dict(source='property',property='kind',value=k,logic='is') for k in shape_kinds.get(shape,[])])
    # プロパティはフィルタ用。点の立場色を種類色で上書きしない。
    for key in ['side','kind','availability']:
        data['additionalProperties'][key]={'graph':True,'localgraph':False}
        data['interactiveSettings'][key]=dict(colormap='winter',colors=[],unselected=[],
            excludeRegex={'regex':'','flags':''},noneType='未設定',showOnGraph=False,
            enableByDefault=True,useForNodeColor=False)
    options=graph_options()
    options.update(textFadeMultiplier=.3,nodeSizeMultiplier=1.35,lineSizeMultiplier=.8,
                   linkDistance=140,linkStrength=.85,centerStrength=.5,repelStrength=10)
    state=dict(id=STATE_ID,name='模擬裁判｜論証の本筋',engineOptions=options,
               pinNodes={},toggleTypes={},logicTypes={},enableLayers=False,currentLayerLevel=0,
               hiddenLegendRows=[],collapsedLegendRows=['side','kind','availability'])
    existing=next((s for s in data['states'] if s.get('id')==STATE_ID),None)
    if existing:existing.update(state)
    else:data['states'].append(state)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('OK: Extended Graph・個別サイズ・種類別形状・立場色・自然な物理配置を設定')


if __name__=='__main__':configure(Path(__file__).resolve().parents[1])
