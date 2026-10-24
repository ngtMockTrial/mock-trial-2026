from pathlib import Path
import json, html, math, re, xml.etree.ElementTree as ET
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.colors import HexColor, Color

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '図解'
OUT.mkdir(exist_ok=True)
(OUT / 'SVG').mkdir(exist_ok=True)
(OUT / '編集用').mkdir(exist_ok=True)
(ROOT / '作成用' / '図解確認用').mkdir(exist_ok=True)
W, H = 1600, 1130
pdfmetrics.registerFont(TTFont('JP',r'C:\Windows\Fonts\meiryo.ttc',subfontIndex=0))
pdfmetrics.registerFont(TTFont('JPB',r'C:\Windows\Fonts\meiryob.ttc',subfontIndex=0))
COLORS = {
 'goal':('#203f59','#203f59','#ffffff','要証事実又は検討対象'),
 'fact':('#eef5fc','#4577a5','#17283b','認定する事実'),
 'evidence':('#f4f5f7','#7f8a96','#17283b','証拠資料'),
 'infer':('#edf7ef','#4e805a','#17283b','検察側の推認'),
 'pending':('#fff6e3','#b17b1a','#49350c','主張又は要確認'),
 'counter':('#fff0ef','#af554c','#662e29','反対事情又は限界'),
 'person':('#f2eff8','#806b9c','#342947','人物又は場所'),
}
EDGE_COLORS={'認定':'#4577a5','推認':'#4e805a','条件':'#a87512','反対':'#ad5148','関係':'#806b9c','時系列':'#536b7a','参照':'#7f8a96'}
DIAGS=[]
def diagram(title, subtitle, notes):
    d={'number':len(DIAGS)+1,'title':title,'subtitle':subtitle,'notes':notes,'nodes':[],'edges':[]};DIAGS.append(d);return d
def node(d,id,kind,text,x,y,w,h,ref=''):
    d['nodes'].append({'id':id,'kind':kind,'text':text,'x':x,'y':y,'w':w,'h':h,'ref':ref});return id
def edge(d,a,b,label,kind='認定',start='top',end='bottom',sx=.5,tx=.5,points=None,label_at=None):
    d['edges'].append({'id':f'L{len(d["edges"])+1:02}','source':a,'target':b,'label':label,'kind':kind,'start':start,'end':end,'sx':sx,'tx':tx,'points':points,'label_at':label_at})
def three(d, ids, kinds, texts, y=405,h=130,refs=None):
    refs=refs or ['']*3
    for x,id,k,t,r in zip([45,585,1125],ids,kinds,texts,refs):node(d,id,k,t,x,y,430,h,r)
def four(d,ids,kinds,texts,y=780,h=140,refs=None):
    refs=refs or ['']*4
    for x,id,k,t,r in zip([35,435,835,1235],ids,kinds,texts,refs):node(d,id,k,t,x,y,330,h,r)

d=diagram('図の読み方と推論の段階','下の証拠から上の要証事実へ読む。各矢印の説明を確認する。',[
 '青の実線は証拠による認定、緑の破線は推認。色と線だけでなく、文字でも関係を示す。',
 '要証事実の箱は検察側が証明すべき主張を示す。箱があるだけで証明済みを意味しない。',
 '教材p.は紙面下部の通し番号。PDF表示ページは教材p.+2。図番号はdraw.ioのタブと一致。'])
node(d,'Y','goal','要証事実の例\n木村が岸井を刺したという犯人性',480,125,640,140,'検察側が証明する主張の例：起訴状 教材p.1')
three(d,['I1','I2','I3'],['infer','infer','infer'],['眼鏡の所有・血液・発見場所から\n現場との接点を評価','清掃状況と落下時刻の説明から\n昼の落下という説明を評価','自転車・映像・動機を\n犯人性の補助事情として評価'],refs=['詳細 図04','詳細 図05','詳細 図06-08'])
four(d,['E','F','P','C'],['evidence','fact','pending','counter'],['証拠資料\n甲1・甲2・乙1など','間接事実\n眼鏡の所在や血液の由来','実演で要確認\n甲3・乙2の準備内容','反対事情・別の説明\n見落としや第三者の使用'],refs=['採用の範囲：教材p.2','証拠が支える範囲を区別','調書自体は採否留保','採用済み事実と主張を区別'])
edge(d,'E','F','例示：証拠から事実を認定','認定',start='top',end='top',points=[(200,715),(600,715)],label_at=(400,700))
edge(d,'F','I1','事実から推認','推認',tx=.65,label_at=(645,655))
edge(d,'P','I2','証言の実際の内容を確認','条件',tx=.65,label_at=(990,650))
edge(d,'C','I3','推論の強さを検討','反対',label_at=(1370,650))
for i,id in enumerate(['I1','I2','I3']):edge(d,id,'Y','組み合わせて判断','推認',tx=[.15,.5,.85][i])

d=diagram('事件全体の立証ピラミッド','要証事実を犯人性・殺意・死亡との因果関係に分ける。',[
 '犯人性の根拠と、傷から死亡したことの根拠を混同しない。',
 '起訴状の20時30分頃という時刻は主張。独立した時刻鑑定として扱わない。',
 '甲3・乙2は採否留保。実演の発言を確認した箇所だけ、供述を使った評価に進む。'])
node(d,'Y','goal','木村による殺人という検察側の主張\n犯人性・殺意・行為と死亡との関係を立証する',430,120,740,120,'起訴状 教材p.1　証明済みの意味ではない')
three(d,['P','M','D'],['infer','infer','fact'],['犯人性\n岸井を刺したのが木村である','殺意\n死亡の危険を認識して刺した','因果関係\n刺創による出血性ショックで死亡'],y=385,h=145,refs=['主争点。詳細 図03','推認の根拠と限界は図11','傷と死因の関係は図10'])
four(d,['G','B','L','W'],['fact','fact','fact','evidence'],['現場に木村の眼鏡\n岸井の血液が付着','共用自転車の血液\n映像・清掃の検討','岸井への怒り\n駐車場の認識','検案結果\n胸腹部等の複数の刺創'],refs=['甲1 教材p.3-4・7／図04','甲1 p.4-6／図05-07','甲2 p.16-19／図08','甲1 p.3／図10-11'])
for i,id in enumerate(['P','M','D']):edge(d,id,'Y',['行為者の特定','故意の認定','死亡との関係'][i],'推認' if i<2 else '認定',tx=[.16,.5,.84][i])
edge(d,'G','P','現場との接点','推認',tx=.2)
edge(d,'B','P','使用者等の限界を含め評価','推認',tx=.8,label_at=(650,654))
edge(d,'L','P','動機の補助事情','推認',tx=.95,points=[(1000,655),(460,655)],label_at=(995,692))
edge(d,'W','M','胸腹部への複数の刺突','推認',tx=.85,points=[(1400,615),(950,615)],label_at=(1175,596))
edge(d,'W','D','検案結果が死因を示す','認定',tx=.5,label_at=(1400,690))

d=diagram('犯人性の総合ピラミッド','中心は眼鏡。清掃・自転車・映像・動機の意味と限界を重ねる。',[
 '各事情を一つの経過として評価する。同じ眼鏡の血液・指紋・皮膚片を独立証拠の数として足さない。',
 '共用自転車と顔の分からない映像だけでは木村を特定できない。',
 '昼に落とした眼鏡に後から血が付いた説明を、清掃の実際の観察条件と照合する。'])
node(d,'P','goal','要証事実\n岸井を刺した人物は木村である',520,120,560,110,'検察側が立証する中心争点')
three(d,['I1','I2','I3'],['infer','infer','infer'],['犯行時の現場との接点\n眼鏡の所在・血液と落下時刻を評価','自転車利用の可能性\n血液・通常利用・移動方向を評価','被害者を対象とする背景\n怒りと駐車場の認識を評価'],y=380,h=145,refs=['詳細 図04-05','詳細 図06-07','詳細 図08'])
four(d,['E2','E10','E4','E8'],['evidence','pending','evidence','evidence'],['木村の眼鏡が現場にあり\n岸井の血液が付いていた','18時頃の清掃と\n眼鏡を見なかったとの説明','共用自転車の岸井の血液\n木村も普段利用','12月24日のLINE\n岸井を許さない・駐車場で見る'],refs=['甲1 p.3-4・7','甲3 p.22。実演で要確認','甲1 p.4-5・8、乙1 p.25','甲2 p.19'])
for i,id in enumerate(['I1','I2','I3']):edge(d,id,'P','総合して犯人性を推認','推認',tx=[.12,.5,.88][i])
edge(d,'E2','I1','所在と血液から接点','推認',tx=.22)
edge(d,'E10','I1','昼の落下説明を検討','条件',tx=.8,label_at=(600,660))
edge(d,'E4','I2','共用性を含め評価','推認',label_at=(980,662))
edge(d,'E8','I3','動機・場所の認識','推認')

d=diagram('眼鏡の証拠から現場との接点へ','所有者の認定と、犯行時に装着していたという推認を区別する。',[
 '眼鏡の所有・発見位置・血液の由来は甲1が支える。付着時刻や装着中かどうかは未確定。',
 '血の模様から刺突時の装着や飛沫方向を科学的に断定する鑑定はない。',
 '昼の落下説明と清掃証言の関係は図05。論告では実演結果に合わせて推認の強さを調整する。'])
node(d,'I','goal','検察側の推認\n木村と犯行時の現場との接点がある',450,115,700,115,'この接点だけで刺突者が確定するわけではない')
three(d,['F1','F2','F3'],['fact','fact','fact'],['発見された眼鏡は木村の物','眼鏡に岸井由来の血液が付着','眼鏡は被害者近辺のB地点で発見'],y=375,h=135,refs=['甲1 p.4','甲1 p.4','甲1 p.3・6・11・14'])
four(d,['E3','EB','EP','R'],['evidence','evidence','evidence','counter'],['本人が所有を認めた\n指紋・皮膚片が一致','血液のDNA型が\n岸井と一致','警察官による発見状況\n見取図と現場写真','昼に落とした後で\n別人の犯行により血が付いた'],refs=['甲1 p.4','甲1 p.4','甲1 p.3・6・11・14','弁護側の説明 p.34'])
edge(d,'E3','F1','所有を認定','認定')
edge(d,'EB','F2','血液の由来を認定','認定',tx=.4,label_at=(630,650))
edge(d,'EP','F3','現場での所在を認定','認定',tx=.3,label_at=(1120,645))
for i,id in enumerate(['F1','F2','F3']):edge(d,id,'I',['持ち主を結ぶ','被害者を結ぶ','現場を結ぶ'][i],'推認',tx=[.14,.5,.86][i])
edge(d,'R','I','付着時刻・落下時刻に疑い','反対',start='right',end='right',points=[(1578,850),(1578,168)],label_at=(1435,275))

d=diagram('清掃から眼鏡の落下時刻を考える','見なかったことから存在しなかったと推認するには、発見できる条件が必要。',[
 '甲3は採否留保。以下の清掃内容は準備情報であり、実演で同内容の証言が得られた場合に評価する。',
 '18時50分の退勤記録は甲1 p.5。B地点の観察範囲・18時到着・滞在時間までは証明しない。',
 '観察範囲が曖昧なら「清掃後に落ちた」と断定せず、論告の清掃段落Bへ変更する。'])
node(d,'I','goal','条件付きの推認\n昼からB地点に眼鏡が残っていたとの説明は採りにくい',410,115,780,120,'見落とし・移動の可能性も含めて判断')
three(d,['P1','P2','R'],['pending','pending','counter'],['18時頃の清掃で\n眼鏡を見なかったとの証言','B地点にあれば\n発見できたといえる観察条件','見落としの可能性\n日没後・急ぎ・車や物の陰'],y=390,h=145,refs=['準備：甲3 p.22','実演で具体的に確認する','甲1 p.6、準備：甲3 p.21-22'])
four(d,['S','V','Q','K'],['pending','pending','pending','pending'],['清掃の経路と向き\nB地点への接近と確認範囲','照明と地面の見え方\n視力1.0という説明','故障対応で作業が遅れ\n19時の家族の約束で急ぐ','木村の落下説明\n記憶か、翌日の推測か'],refs=['準備：甲3 p.22','甲1 p.6・12-14、甲3 p.22','準備：甲3 p.21-22','準備：乙2 p.28-29'])
edge(d,'P1','I','未発見という証言','条件',tx=.18)
edge(d,'P2','I','発見できる条件が必要','条件',tx=.53)
edge(d,'R','I','推認を弱める','反対',tx=.88)
edge(d,'S','P2','範囲を確認','条件',tx=.15,label_at=(350,660))
edge(d,'V','P2','見え方を確認','条件',tx=.55,label_at=(710,665))
edge(d,'Q','R','注意の程度を検討','条件',tx=.45,label_at=(1190,665))
edge(d,'K','I','落下説明との整合を検討','条件',start='right',end='right',points=[(1578,850),(1578,175)],label_at=(1425,275))

d=diagram('共用自転車と使用者の推認','事件との接点を示す事実と、木村が当日使用したという推認を分ける。',[
 '血液の付着時刻・経緯や、犯行当日の使用者は特定されていない。',
 '指紋は通常の利用でも付く。他人の指紋があることを無視して「木村専用」と扱わない。',
 '映像の自転車との同一性は未確定。図07の時刻・方向は補助事情として関連付ける。'])
node(d,'I','goal','検察側の推認の検討\n木村が事件に関係して自転車を使った可能性',430,115,740,120,'当日の使用を断定できる証拠ではない')
three(d,['F1','F2','F3'],['fact','fact','counter'],['自転車の右ハンドルに\n岸井の血液が付いていた','木村が普段使う自転車が\n自宅の共同住宅の駐輪場にあった','住民が共同使用・無施錠\n外部からも出入り可能'],y=385,h=145,refs=['甲1 p.4-5・8','甲1 p.4-5、乙1 p.25','甲1 p.4-5'])
four(d,['E4B','E4F','E9','E4O'],['evidence','evidence','evidence','evidence'],['自転車の血液の\nDNA型が岸井と一致','複数の指紋の一部が\n木村と一致','買い物などで\n本件自転車を使うとの供述','住民への聴き取り\n他人の指紋は未特定'],refs=['甲1 p.5','甲1 p.5','乙1 p.25。採用済み','甲1 p.4-5'])
edge(d,'E4B','F1','血液の由来を認定','認定')
edge(d,'E4F','F2','木村との接点','認定',tx=.25,label_at=(645,660))
edge(d,'E9','F2','通常利用を認定','認定',tx=.8,label_at=(1000,660))
edge(d,'E4O','F3','第三者も使える','認定')
edge(d,'F1','I','事件との接点','推認',tx=.15)
edge(d,'F2','I','木村との接点','推認',tx=.5)
edge(d,'F3','I','使用者を一人に絞れない','反対',tx=.85)

d=diagram('防犯映像と移動の関係','映像は本人確認ではなく、時刻と進行方向の整合を考える補助事情。',[
 '写真③は逮捕直後の木村の服装。事件当日の服装を示す証拠として用いない。',
 '起訴状の20時30分頃は検察の主張であり、映像から刺突時刻が判明したわけではない。',
 '道路上の位置関係と映像の走行方向が整合しても、現場から木村宅へ帰ったことまでは確認できない。'])
node(d,'I','goal','補助的な評価\n検察側が想定する移動の時刻・方向と整合する',425,115,750,115,'映像の人物が木村だという要証事実は証明しない')
three(d,['F1','F2','R'],['fact','fact','counter'],['20時32分頃\n男性が自転車で北から南へ進む','駐車場の南約200mにコンビニ\n木村宅は駐車場の南約400m','顔が判別できない\n押収自転車との同一性も未確定'],y=395,h=145,refs=['甲1 p.5・10','甲1 p.6・13','甲1 p.5。特定を示す記載なし'])
three(d,['E5','E7','YTIME'],['evidence','evidence','pending'],['防犯カメラ映像と写真④','現場見取図1と距離の報告','犯行は20時30分頃\nという起訴事実の主張'],y=790,h=140,refs=['甲1 p.5・10','甲1 p.6・13','起訴状p.1。独立した時刻鑑定ではない'])
edge(d,'E5','F1','時刻と走行方向','認定')
edge(d,'E7','F2','南北の位置関係','認定')
edge(d,'YTIME','I','主張時刻との比較','条件',start='right',end='right',points=[(1578,855),(1578,170)],label_at=(1430,285))
edge(d,'F1','I','時刻・進行方向を照合','推認',tx=.15)
edge(d,'F2','I','自宅方向との整合','推認',tx=.5)
edge(d,'R','I','本人特定には使えない','反対',tx=.85)

d=diagram('LINEから動機と所在の認識へ','メッセージの存在、感情の推認、実際の殺害行為を分ける。',[
 '岸井と本所の実際の交際をLINEだけで確定せず、木村がどう受け止めていたかを評価する。',
 '10月の復縁要求が、犯行日まで同じ強さで続いたと自動的に決めない。',
 '怒りや未練は犯行そのものの証明ではなく、物的接点を検討する補助事情。'])
node(d,'I','goal','動機と場所の認識の推認\n岸井への怒りと、駐車場で会えるという認識',430,115,740,120,'犯人性を補助する事情。殺害の実行は別に立証')
three(d,['F1','F2','F3'],['fact','fact','fact'],['交際解消後に\n復縁を求める送信が続いた','12月24日に岸井を\n許さない趣旨のメッセージ','岸井を自宅近くの駐車場で\nよく見ると送信した'],y=395,h=145,refs=['甲2 p.17-19','甲2 p.19','甲2 p.19'])
three(d,['E81','E82','E83'],['evidence','evidence','evidence'],['10月25日の別れの通告と\n10月26日以降のLINE履歴','12月24日18時台のLINE\n岸井に対する怒りの表現','12月24日18時14分のLINE\n駐車場でよく見るとの記載'],y=790,h=140,refs=['甲2 p.17-19','甲2 p.19','甲2 p.19'])
for a,b,lab in [('E81','F1','送信の内容を認定'),('E82','F2','怒りの表現を認定'),('E83','F3','記載内容を認定')]:edge(d,a,b,lab)
for i,id in enumerate(['F1','F2','F3']):edge(d,id,'I',['未練という背景','岸井への感情','場所の認識'][i],'推認',tx=[.15,.5,.85][i])

d=diagram('人物と駐車場の関係','人物間の関係と、現場を知る立場を示す。各線は犯行の証明を意味しない。',[
 '木村と岸井が高校の同級生という準備情報は乙2 p.30。実演で確認する。',
 '本所と岸井の実際の交際は、木村のLINEだけでは確定しない。矢印は木村の認識を示す。',
 '大滝は清掃担当、大林は発見・通報者。二人の役割と証言対象を混同しない。'])
node(d,'H','person','本所マサミ\n木村のLINEの相手',585,125,430,125,'甲2 教材p.15-19')
node(d,'K','person','木村忠太\n被告人・眼鏡の持ち主',45,405,430,125,'甲1 p.4、甲2 p.19')
node(d,'S','person','岸井新之助\n被害者・駐車場の契約者',1125,405,430,125,'甲1 p.3・6')
three(d,['O','P','B'],['pending','person','person'],['大滝悟郎\n清掃状況を説明する証人','本件駐車場\nAは被害者、Bは眼鏡の発見地点','大林銀弥\n被害者を発見し110番'],y=805,h=145,refs=['準備：甲3 p.20-22','甲1 p.3・6・11・14','甲1 p.3'])
edge(d,'K','H','交際解消後も復縁を求め送信','関係',tx=.2,label_at=(360,325))
edge(d,'H','K','10月25日に別れを告げる','関係',start='left',end='top',tx=.2,points=[(20,187),(20,350),(131,350)],label_at=(250,365))
edge(d,'K','S','12月24日のLINEで怒りを表す','関係',start='right',end='left',label_at=(800,450))
edge(d,'S','H','本所と交際中だと木村が認識','推認',tx=.8,label_at=(1205,325))
edge(d,'K','P','岸井をよく見ると送信','関係',start='bottom',end='top',label_at=(520,655))
edge(d,'S','P','駐車区画を契約','関係',start='bottom',end='top',tx=.8,label_at=(1080,655))
edge(d,'O','P','担当し清掃したとの説明','条件',start='top',end='top',tx=.25,points=[(260,750),(692.5,750)],label_at=(500,735))
edge(d,'B','P','20時45分頃に発見','関係',start='top',end='top',tx=.75,points=[(1340,750),(907.5,750)],label_at=(1130,735))

d=diagram('刺創から死亡に至る因果関係','傷・死因・死亡をつなぐ。行為者が木村であることは図03で別に立証する。',[
 '甲1の検案結果が、刺創による出血性ショックを死因としている。',
 '傷の順番、深さ、凶器の具体的な型、医療過誤等を示す資料はない。教材にない経過を追加しない。',
 '下段の3箱は同じ甲1の検案・死亡確認の記載を整理したもの。独立した3件の鑑定ではない。'])
node(d,'D','goal','要証事実\n岸井の刺創が死亡を引き起こした',480,115,640,115,'甲1 教材p.3の検案・死亡確認が根拠')
three(d,['W','B','T'],['fact','fact','fact'],['胸腹部・腕・右大腿部に\n複数の刺創があった','これらの傷による\n出血性ショックが死因','搬送先で同日21時55分\n岸井の死亡を確認'],y=405,h=145,refs=['甲1 p.3','甲1 p.3','甲1 p.3'])
three(d,['E1A','E1B','E1C'],['evidence','evidence','evidence'],['検案結果の創傷の記載\n左胸2・右上腹1・両腕複数・右大腿1','検案結果の死因の記載\n上記の傷による出血性ショック','搬送と死亡確認の記載\n五哲大学病院で21時55分'],y=800,h=150,refs=['甲1 p.3 第2の2①','甲1 p.3 第2の2③','甲1 p.3 第2の1'])
for a,b,lab in [('E1A','W','創傷の存在を認定'),('E1B','B','医学的死因を認定'),('E1C','T','死亡の結果を認定')]:edge(d,a,b,lab)
for i,id in enumerate(['W','B','T']):edge(d,id,'D',['行為の結果としての傷','傷による死因','死亡という結果'][i],'認定',tx=[.15,.5,.85][i])

d=diagram('刺突行為から殺意を推認する','殺意の推認を、犯人性の立証から分けて整理する。',[
 'ここで示すのは刺した者の意思の推認。木村が刺したことを、傷の存在だけで証明できるわけではない。',
 '凶器未発見。刃渡り・傷の深さ・力の強さ・刺突の順番を具体的に認定する資料はない。',
 '両腕の刺創を防御創と断定したり、全ての傷が同じ深さだったと仮定したりしない。'])
node(d,'M','goal','要証事実\n死亡の危険を認識し、容認して刺したという殺意',430,115,740,115,'検察側の推認。犯人性は別に立証する')
three(d,['I1','I2','R'],['infer','fact','counter'],['生命に関わる胸腹部への刺突\n死亡の危険を理解し得る行為と評価','複数の部位に刺創\n一度の軽い接触とは異なる傷の状況','凶器・創の深さ・刺突順序は不明\n具体的な刺し方を作って補わない'],y=395,h=150,refs=['甲1 p.3からの検察側の評価','甲1 p.3','甲1 p.3及び記載の範囲'])
three(d,['E1X','E1Y','E1Z'],['evidence','evidence','evidence'],['検案結果\n左胸2か所・右上腹1か所の刺創','検案結果\n両腕複数・右大腿1か所の刺創','検案結果\n凶器は刃物と考えられるが未発見'],y=800,h=150,refs=['甲1 p.3 第2の2①','甲1 p.3 第2の2①','甲1 p.3 第2の2②・3'])
edge(d,'E1X','I1','部位を踏まえ評価','推認')
edge(d,'E1Y','I2','刺創の複数性を認定','認定')
edge(d,'E1Z','R','資料から分かる範囲','認定')
edge(d,'I1','M','行為の危険性から意思を推認','推認',tx=.15)
edge(d,'I2','M','行為の反復性を併せ評価','推認',tx=.5)
edge(d,'R','M','推認の限界','反対',tx=.85)

d=diagram('弁護側の説明と検察側の確認課題','反対事情が、どの推論に影響するかを示す。',[
 '弁護側の説明は教材p.34-35と乙2 p.27-31を参照。乙2の細部は実演で確認する。',
 '被告人に無実や別人の犯行の証明を求めない。証拠全体から残る合理的な疑いを検討する。',
 '清掃証言が具体的に裏付けられなければ、眼鏡の落下時刻の推認を弱め、結びも再検討する。'])
node(d,'Q','goal','最終的な検討対象\n木村の犯人性に合理的な疑いが残るか',450,115,700,115,'立証責任は検察官。詳細は既存資料01')
three(d,['R1','R2','R3'],['counter','counter','counter'],['昼に眼鏡を落とし\n別人の犯行時に血が付いたとの説明','大滝が清掃で\n眼鏡を見落とした可能性','共用自転車を別人が使用\n映像も木村と特定できない'],y=385,h=150,refs=['弁護冒頭陳述 p.34','準備：甲3 p.21-22','甲1 p.4-5、弁護主張 p.34'])
three(d,['C1','C2','C3'],['pending','pending','fact'],['落下の記憶と推測を分ける\n具体的な場所を実演で確認','B地点の経路・向き・見え方\n急ぎによる作業の変化を確認','他人の指紋・無施錠・開放駐輪場\n映像の顔が判別不能'],y=800,h=150,refs=['準備：乙2 p.28-29','準備：甲3 p.21-22','甲1 p.4-5'])
edge(d,'C1','R1','説明の確かさを検討','条件')
edge(d,'C2','R2','見落としの程度を検討','条件')
edge(d,'C3','R3','別人説に関わる客観事情','認定')
for i,id in enumerate(['R1','R2','R3']):edge(d,id,'Q',['現場との接点の評価に影響','清掃後の落下推認に影響','使用者・本人特定に影響'][i],'反対',tx=[.15,.5,.85][i])

d=diagram('事件当日の時系列と確かさ','前後関係を示す図。矢印は因果関係や同一人物の行動連続性を意味しない。',[
 '14時15分頃の転倒・眼鏡落下は本人の説明の準備情報。18時頃の清掃も実演で確認する。',
 '20時30分頃は起訴状の犯行時刻の主張。独立の時刻鑑定として扱わない。',
 '夜間写真は2026年1月6日撮影で、事件当夜の写真ではない。甲1 p.6・12。'])
events=[
 ('T1','fact','14時頃\n木村がお好み焼き店にいた','甲1 p.6'),
 ('T2','pending','14時15分頃\n駐車場付近で転倒したとの説明','準備：乙2 p.27-29'),
 ('T3','fact','17時04分\n日没','甲1 p.6'),
 ('T4','pending','18時頃\n大滝が清掃したとの説明','準備：甲3 p.22'),
 ('T5','fact','18時50分\n大滝が退勤','甲1 p.5'),
 ('T6','pending','20時30分頃\n検察側が主張する犯行時刻','起訴状 p.1'),
 ('T7','fact','20時32分頃\n男性の自転車が南向きに走行','甲1 p.5・10'),
 ('T8','fact','20時45分頃\n大林が被害者を発見し通報','甲1 p.3'),
 ('T9','fact','20時50分頃\n警察官が臨場。呼吸あり','甲1 p.3'),
 ('T10','fact','21時頃\n警察官が眼鏡を発見','甲1 p.3-4'),
 ('T11','fact','21時55分\n搬送先で死亡確認','甲1 p.3'),
]
positions=[(45,180),(445,180),(845,180),(1245,180),(1245,455),(845,455),(445,455),(45,455),(45,755),(445,755),(845,755)]
for (id,k,txt,ref),(x,y) in zip(events,positions):node(d,id,k,txt,x,y,305,155,ref)
for i in range(len(events)-1):
    a,b=events[i][0],events[i+1][0];x1,y1=positions[i];x2,y2=positions[i+1]
    if y1==y2:
        forward=x2>x1;edge(d,a,b,'次','時系列',start='right' if forward else 'left',end='left' if forward else 'right',points=[],label_at=((x1+x2+305)/2,y1+70))
    else:edge(d,a,b,'次','時系列',start='bottom',end='top',points=[],label_at=(x1+152,y1+217))

d=diagram('証拠の採否と論告に至る経路','書証の採用と、法廷で実際に述べた供述を区別する。',[
 '根拠：教材p.2の証拠整理メモ。実演で採否や取調べについて説明があれば、その内容を記録する。',
 '冒頭陳述と起訴状は主張の範囲を示す。記載されているだけで事実の証明にはならない。',
 '甲3・乙2の調書を、確認なしに採用済み証拠へ変更しない。実演の発言を別途記録して使う。'])
node(d,'U','goal','論告で根拠として使う事実と推認\n採用済み証拠と、実演で確認した供述に基づく',400,115,800,115,'証拠の採否：教材p.2')
three(d,['A','P','Q'],['fact','pending','pending'],['採用された書証\n内容が支える範囲で事実を認定','大滝の実際の法廷証言\nB地点の観察状況を記録','木村の実際の法廷供述\n落下・所在・利用の説明を記録'],y=395,h=145,refs=['甲1・甲2・乙1','証人として採用。実際の発言を確認','被告人質問で実際の発言を確認'])
four(d,['EA','EP','EQ','M'],['evidence','pending','pending','counter'],['甲1・甲2・乙1\n同意・採用','甲3 大滝の調書\n不同意・採否留保','乙2 木村の調書\n不同意・採否留保','起訴状・冒頭陳述\n立証予定の主張'],refs=['教材p.2','教材p.20-23','教材p.27-31','教材p.1・32-35'])
edge(d,'EA','A','書証として使用','認定',tx=.4)
edge(d,'EP','P','質問の準備に使う','条件',label_at=(670,660))
edge(d,'EQ','Q','質問の準備に使う','条件',label_at=(1170,660))
edge(d,'A','U','資料の内容に基づく','認定',tx=.15)
edge(d,'P','U','実演の発言を確認して使用','条件',tx=.5)
edge(d,'Q','U','実演の発言を確認して使用','条件',tx=.85)
edge(d,'M','U','主張だけでは証明にならない','反対',start='right',end='right',points=[(1578,850),(1578,172)],label_at=(1410,285))

d=diagram('人物と物と場所の接点','眼鏡・自転車・血液・指紋・発見場所が、誰をどう結ぶかを一覧にする。',[
 '所有者、登録名義人、普段の利用者、犯行当日の利用者は別の問題。登録名義だけで使用者を決めない。',
 '岸井の血液が眼鏡・自転車に付着した事実と、木村が犯行時に使用したという推認を分ける。',
 '各線は物との接点を示す。血液の付着時刻や、木村による刺突の直接証拠を示す線ではない。'])
node(d,'K','person','木村忠太\n眼鏡の持ち主・自転車の通常利用者',45,145,430,130,'甲1 p.4-5、乙1 p.25')
node(d,'S','person','岸井新之助\n眼鏡と自転車に血液が付着',1125,145,430,130,'甲1 p.4-5')
node(d,'G','fact','血痕付き眼鏡\n木村の指紋と皮膚片も確認',45,540,430,140,'甲1 p.4')
node(d,'Y','person','矢野天彦\n自転車の登録名義人',585,540,430,140,'甲1 p.5。2012年以降県外転出')
node(d,'B','fact','血痕付き共用自転車\n木村を含む複数人の指紋',1125,540,430,140,'甲1 p.4-5・8')
node(d,'P','person','本件駐車場\n岸井の近辺のB地点で眼鏡を発見',45,820,430,140,'甲1 p.3・6・11・14')
node(d,'H','person','ハイツ京極の駐輪場\n1月5日に自転車を発見',1125,820,430,140,'甲1 p.4-5。外部からも出入り可能')
edge(d,'K','G','所有・指紋・皮膚片','関係',start='bottom',end='top',label_at=(260,380))
edge(d,'S','B','血液のDNA型が一致','関係',start='bottom',end='top',label_at=(1340,400))
edge(d,'S','G','血液のDNA型が一致','関係',start='left',end='top',tx=.8,points=[(930,210),(930,335),(389,335)],label_at=(695,317))
edge(d,'K','B','通常利用・指紋が一致','関係',start='right',end='top',tx=.2,points=[(670,210),(670,450),(1211,450)],label_at=(930,430))
edge(d,'Y','B','登録名義。現使用者とは限らない','関係',start='bottom',end='left',points=[(800,730),(1080,730),(1080,610)],label_at=(930,710))
edge(d,'G','P','現場で発見','関係',start='bottom',end='top',label_at=(260,755))
edge(d,'B','H','住宅の駐輪場で発見','関係',start='bottom',end='top',label_at=(1340,755))

def wrap(text, width, size, font='JP'):
    lines=[]
    for para in text.split('\n'):
        current=''
        for ch in para:
            if current and pdfmetrics.stringWidth(current+ch,font,size)>width:
                lines.append(current);current=ch
            else:current+=ch
        lines.append(current)
    return lines

def prepared_node(n):
    fontsize=21 if n['kind']=='goal' else 20
    body=wrap(n['text'],n['w']-28,fontsize,'JPB' if n['kind']=='goal' else 'JP')
    refs=wrap(n['ref'],n['w']-28,13.5)
    needed=25+len(body)*(fontsize*1.32)+(len(refs)*17 if n['ref'] else 0)+18
    if needed>n['h']:
        fontsize=18
        body=wrap(n['text'],n['w']-28,fontsize,'JPB' if n['kind']=='goal' else 'JP')
        needed=25+len(body)*(fontsize*1.32)+(len(refs)*17 if n['ref'] else 0)+18
    assert needed<=n['h']+1,(n['id'],n['text'],needed,n['h'])
    return fontsize,body,refs

def anchor(n,side,t):
    if side=='top':return (n['x']+n['w']*t,n['y'])
    if side=='bottom':return(n['x']+n['w']*t,n['y']+n['h'])
    if side=='left':return(n['x'],n['y']+n['h']*t)
    return(n['x']+n['w'],n['y']+n['h']*t)

def route(d,e):
    by={n['id']:n for n in d['nodes']};a=anchor(by[e['source']],e['start'],e['sx']);b=anchor(by[e['target']],e['end'],e['tx'])
    if e['points'] is not None:pts=[a]+[tuple(x) for x in e['points']]+[b]
    elif abs(a[0]-b[0])<2 or abs(a[1]-b[1])<2:pts=[a,b]
    else:
        ym=(a[1]+b[1])/2;pts=[a,(a[0],ym),(b[0],ym),b]
    return pts

def middle(pts):
    distances=[math.dist(a,b) for a,b in zip(pts,pts[1:])];remain=sum(distances)/2
    for a,b,dist in zip(pts,pts[1:],distances):
        if dist>=remain and dist:
            k=remain/dist;return(a[0]+(b[0]-a[0])*k,a[1]+(b[1]-a[1])*k)
        remain-=dist
    return pts[-1]

def overlap(a,b):
    return a[0]<b[0]+b[2] and a[0]+a[2]>b[0] and a[1]<b[1]+b[3] and a[1]+a[3]>b[1]

def distance_to_route(x,y,pts):
    out=[]
    for (ax,ay),(bx,by) in zip(pts,pts[1:]):
        dx,dy=bx-ax,by-ay;den=dx*dx+dy*dy;k=max(0,min(1,((x-ax)*dx+(y-ay)*dy)/den)) if den else 0
        out.append(math.hypot(x-ax-k*dx,y-ay-k*dy))
    return min(out)

def layout_labels(d):
    occupied=[]
    for e in d['edges']:
        pts=route(d,e);mx,my=middle(pts);pref=e['label_at'] or (mx,my-18)
        size=14 if e['kind']=='時系列' else 16
        e['_label_size']=size
        label=e['kind']+'　'+e['label'];ll=wrap(label,270,size)
        width=max(pdfmetrics.stringWidth(x,'JP',size) for x in ll)+12;height=len(ll)*22+6
        candidates=[pref]
        for a,b in zip(pts,pts[1:]):
            for k in [.5,.25,.75,.1,.9]:
                x=a[0]+(b[0]-a[0])*k;y=a[1]+(b[1]-a[1])*k
                for dx,dy in [(0,-23),(0,26),(0,-47),(0,50),(width/2+15,0),(-width/2-15,0),(0,-70),(0,73)]:candidates.append((x+dx,y+dy))
        candidates.sort(key=lambda q:math.dist(q,pref))
        chosen=None
        for x,y in candidates:
            box=(x-width/2,y-height/2,width,height)
            if box[0]<10 or box[0]+width>1590 or box[1]<112 or box[1]+height>967:continue
            if distance_to_route(x,y,pts)>85:continue
            if any(overlap(box,(n['x']-3,n['y']-3,n['w']+6,n['h']+6)) for n in d['nodes']):continue
            if any(overlap(box,other) for other in occupied):continue
            chosen=(x,y);occupied.append(box);break
        assert chosen is not None,('label placement',d['number'],e['id'],label)
        e['label_at']=chosen;e['_label_lines']=ll;e['_label_bbox']=(chosen[0]-width/2,chosen[1]-height/2,width,height)

def arrow_points(pts,kind):
    end=pts[-1];prev=next((p for p in reversed(pts[:-1]) if math.dist(p,end)>.1),pts[-2]);dx,dy=end[0]-prev[0],end[1]-prev[1];length=math.hypot(dx,dy);ux,uy=dx/length,dy/length
    if kind=='反対':return [(end[0]-uy*7,end[1]+ux*7),(end[0]+uy*7,end[1]-ux*7)]
    return [end,(end[0]-ux*12-uy*5,end[1]-uy*12+ux*5),(end[0]-ux*12+uy*5,end[1]-uy*12-ux*5)]

def node_label(n):
    fs,body,refs=prepared_node(n);typ=COLORS[n['kind']][3]
    label=f'<div style="font-family:Meiryo;font-size:14px;">{html.escape(n["id"])}　{typ}</div>'
    label+=f'<div style="font-family:Meiryo;font-size:{fs}px;line-height:1.32;'+('font-weight:bold;' if n['kind']=='goal' else '')+'">'+'<br>'.join(html.escape(s) for s in body)+'</div>'
    if n['ref']:label+='<div style="font-family:Meiryo;font-size:13.5px;margin-top:4px;">'+'<br>'.join(html.escape(s) for s in refs)+'</div>'
    return label

def drawio_file():
    root=ET.Element('mxfile',{'host':'app.diagrams.net','type':'device','pages':str(len(DIAGS))})
    for d in DIAGS:
        page=ET.SubElement(root,'diagram',{'id':f'diagram-{d["number"]:02}','name':f'{d["number"]:02} {d["title"]}'})
        model=ET.SubElement(page,'mxGraphModel',{'dx':str(W),'dy':str(H),'grid':'1','gridSize':'10','guides':'1','tooltips':'1','connect':'1','arrows':'1','fold':'1','page':'1','pageScale':'1','pageWidth':str(W),'pageHeight':str(H),'math':'0','shadow':'0'})
        cells=ET.SubElement(model,'root');ET.SubElement(cells,'mxCell',{'id':'0'});ET.SubElement(cells,'mxCell',{'id':'1','parent':'0'})
        def textcell(id,text,x,y,w,h,size=20):
            c=ET.SubElement(cells,'mxCell',{'id':id,'value':text,'style':f'text;html=0;align=left;verticalAlign=top;whiteSpace=wrap;overflow=hidden;fontFamily=Meiryo;fontSize={size};fontColor=#17283b;','vertex':'1','parent':'1'})
            ET.SubElement(c,'mxGeometry',{'x':str(x),'y':str(y),'width':str(w),'height':str(h),'as':'geometry'})
        textcell('title',f'{d["number"]:02}  {d["title"]}',35,25,1530,44,31)
        textcell('subtitle',d['subtitle'],35,77,1530,38,19)
        for n in d['nodes']:
            fill,stroke,font,_=COLORS[n['kind']]
            style=f'rounded=0;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};strokeWidth=2;fontColor={font};fontFamily=Meiryo;align=left;verticalAlign=middle;spacing=14;overflow=hidden;'
            if n['kind']=='pending':style+='dashed=1;'
            c=ET.SubElement(cells,'mxCell',{'id':n['id'],'value':node_label(n),'style':style,'vertex':'1','parent':'1','classification':n['kind'],'sourceReference':n['ref']})
            ET.SubElement(c,'mxGeometry',{'x':str(n['x']),'y':str(n['y']),'width':str(n['w']),'height':str(n['h']),'as':'geometry'})
        for e in d['edges']:
            a,b=e['start'],e['end'];exitx,exity=({'top':(e['sx'],0),'bottom':(e['sx'],1),'left':(0,e['sx']),'right':(1,e['sx'])})[a];entryx,entryy=({'top':(e['tx'],0),'bottom':(e['tx'],1),'left':(0,e['tx']),'right':(1,e['tx'])})[b]
            style=f'edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;jumpStyle=arc;jumpSize=8;html=0;strokeWidth=2;strokeColor={EDGE_COLORS[e["kind"]]};fontColor={EDGE_COLORS[e["kind"]]};fontSize={e["_label_size"]};fontFamily=Meiryo;labelBackgroundColor=#ffffff;endArrow={"tee" if e["kind"]=="反対" else "block"};endFill=1;exitX={exitx};exitY={exity};exitDx=0;exitDy=0;entryX={entryx};entryY={entryy};entryDx=0;entryDy=0;'
            if e['kind'] in ['推認','条件','反対','参照']:style+='dashed=1;'
            c=ET.SubElement(cells,'mxCell',{'id':e['id'],'value':'\n'.join(e['_label_lines']),'style':style,'edge':'1','parent':'1','source':e['source'],'target':e['target']})
            g=ET.SubElement(c,'mxGeometry',{'relative':'1','as':'geometry'});pts=route(d,e)
            if len(pts)>2:
                ar=ET.SubElement(g,'Array',{'as':'points'})
                for x,y in pts[1:-1]:ET.SubElement(ar,'mxPoint',{'x':str(x),'y':str(y)})
            mx,my=middle(pts);lx,ly=e['label_at'] or(mx,my-15)
            ET.SubElement(g,'mxPoint',{'x':str(lx-mx),'y':str(ly-my),'as':'offset'})
        notes='\n'.join(d['notes'])
        textcell('notes',notes,35,1016,1530,100,16)
    ET.indent(root,space='  ')
    path=OUT/'05_立証ピラミッドと関係図.drawio';ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)
    return path

def render():
    pdfpath=OUT/'05_立証ピラミッドと関係図.pdf';c=canvas.Canvas(str(pdfpath),pagesize=landscape(A3));c.setTitle('検察官の立証ピラミッドと関係図');c.setAuthor('検察官準備資料')
    for d in DIAGS:
        svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1130" viewBox="0 0 1600 1130" role="img"><title>{html.escape(d["title"])}</title><rect width="1600" height="1130" fill="white"/>']
        scale=landscape(A3)[0]/W;c.saveState();c.scale(scale,scale)
        def text(x,y,text,size=20,font='JP',color='#17283b'):
            c.setFont(font,size);c.setFillColor(HexColor(color));c.drawString(x,H-y,text)
            svg.append(f'<text x="{x}" y="{y}" font-family="Meiryo, sans-serif" font-size="{size}" fill="{color}"'+(' font-weight="bold"' if font=='JPB' else '')+'>'+html.escape(text)+'</text>')
        def rect(x,y,w,h,fill,stroke='none',width=0):
            c.setFillColor(HexColor(fill));c.setStrokeColor(HexColor(stroke if stroke!='none' else fill));c.setLineWidth(width);c.rect(x,H-y-h,w,h,fill=1,stroke=stroke!='none')
            svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')
        text(35,54,f'{d["number"]:02}  {d["title"]}',31,'JPB');text(35,94,d['subtitle'],19)
        # Connections are under nodes, while labels are above them.
        for e in d['edges']:
            pts=route(d,e);col=EDGE_COLORS[e['kind']];dash=e['kind'] in ['推認','条件','反対','参照']
            c.setStrokeColor(HexColor(col));c.setLineWidth(2);c.setDash([8,6] if dash else [])
            path=c.beginPath();path.moveTo(pts[0][0],H-pts[0][1])
            for x,y in pts[1:]:path.lineTo(x,H-y)
            c.drawPath(path)
            svg.append('<polyline points="'+' '.join(f'{x},{y}' for x,y in pts)+f'" fill="none" stroke="{col}" stroke-width="2"'+(' stroke-dasharray="8 6"' if dash else '')+'/>')
            c.setDash([]);arr=arrow_points(pts,e['kind']);path=c.beginPath();path.moveTo(arr[0][0],H-arr[0][1])
            for x,y in arr[1:]:path.lineTo(x,H-y)
            c.setFillColor(HexColor(col))
            if e['kind']!='反対':path.close()
            c.drawPath(path,fill=e['kind']!='反対',stroke=1)
            svg.append(('<polyline' if e['kind']=='反対' else '<polygon')+' points="'+' '.join(f'{x},{y}' for x,y in arr)+f'" stroke="{col}" fill="'+('none' if e['kind']=='反対' else col)+'" stroke-width="2"/>')
        for n in d['nodes']:
            fill,stroke,color,typ=COLORS[n['kind']];rect(n['x'],n['y'],n['w'],n['h'],fill,stroke,2)
            fs,body,refs=prepared_node(n);yy=n['y']+23
            text(n['x']+14,yy,n['id']+'　'+typ,14,color=color);yy+=fs*1.28
            for line in body:text(n['x']+14,yy,line,fs,'JPB' if n['kind']=='goal' else 'JP',color);yy+=fs*1.32
            if n['ref']:
                yy=n['y']+n['h']-12-17*(len(refs)-1)
                for line in refs:text(n['x']+14,yy,line,13.5,color=color);yy+=17
        for e in d['edges']:
            x,y=e['label_at'];bx,by,bw,bh=e['_label_bbox'];rect(bx,by,bw,bh,'#ffffff')
            for i,label in enumerate(e['_label_lines']):
                width=pdfmetrics.stringWidth(label,'JP',e['_label_size']);text(x-width/2,by+19+i*22,label,e['_label_size'],color=EDGE_COLORS[e['kind']])
        # Compact legend. Type labels are also present in every node.
        y=985
        for x,kind,label in [(35,'goal','検討対象'),(245,'fact','認定する事実'),(475,'evidence','証拠資料'),(690,'infer','推認'),(900,'pending','主張・要確認'),(1120,'counter','反対事情・限界'),(1380,'person','人物・場所')]:
            fill,stroke,_,_=COLORS[kind];rect(x,y-17,18,18,fill,stroke,1);text(x+26,y,label,15)
        for i,line in enumerate(d['notes']):text(35,1033+i*25,line,15.5)
        c.restoreState();c.showPage();svg.append('</svg>')
        (OUT/'SVG'/f'{d["number"]:02}_{d["title"]}.svg').write_text('\n'.join(svg),encoding='utf-8')
    c.save();return pdfpath

def export_text():
    (OUT/'編集用'/'図の構造データ.json').write_text(json.dumps(DIAGS,ensure_ascii=False,indent=2),encoding='utf-8')
    text=[]
    for d in DIAGS:
        text.extend([f'{d["number"]:02} {d["title"]}',d['subtitle'],''])
        for n in d['nodes']:text.append(f'{n["id"]} [{COLORS[n["kind"]][3]}] {n["text"].replace(chr(10)," / ")}　根拠 {n["ref"]}')
        text.append('')
        for e in d['edges']:text.append(f'{e["source"]} → {e["target"]}　{e["kind"]}　{e["label"]}')
        text.extend(['']+d['notes']+['',''])
    (OUT/'編集用'/'ノードと矢印の一覧.txt').write_text('\n'.join(text),encoding='utf-8-sig')

def index():
    entries=[]
    for d in DIAGS:
        file=f'{d["number"]:02}_{d["title"]}.svg'
        entries.append(f'<section id="d{d["number"]}"><h2>{d["number"]:02} {html.escape(d["title"])}</h2><p>{html.escape(d["subtitle"])}</p><a href="SVG/{html.escape(file)}" target="_blank">図を大きく開く</a><img loading="lazy" src="SVG/{html.escape(file)}" alt="{html.escape(d["title"])}"></section>')
    nav=''.join(f'<a href="#d{d["number"]}">{d["number"]:02} {html.escape(d["title"])}</a>' for d in DIAGS)
    s='''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>立証ピラミッドと関係図</title><style>body{margin:0;background:#f6f8fa;color:#17283b;font:16px/1.8 Meiryo,sans-serif}main{max-width:1400px;margin:auto;padding:36px 24px}h1{font-size:30px;color:#000}h2{font-size:23px;color:#000}a{color:#175989}nav{display:flex;flex-wrap:wrap;gap:8px 20px;margin:24px 0}nav a{font-size:14px}section{background:white;padding:24px;margin:32px 0;border:1px solid #d9dfe5}img{display:block;width:100%;height:auto;margin-top:12px}.downloads a{display:inline-block;margin:0 22px 10px 0}small{font-size:13px}@media print{nav,.downloads{display:none}section{break-before:page;border:0;padding:0}main{padding:0}}</style><main><h1>検察側の立証ピラミッドと関係図</h1><p>下の証拠から上の要証事実へ読みます。矢印の「認定」「推認」「条件」「反対」を区別してください。全図の箱・文字・接続線はdraw.io形式で個別に編集できます。</p><div class="downloads"><a href="05_立証ピラミッドと関係図.drawio" download>編集用draw.ioファイル</a><a href="05_立証ピラミッドと関係図.pdf">印刷用PDF</a><a href="編集方法.txt">編集方法</a><a href="../ここから開く.html">既存資料の入口へ</a></div><nav>NAV</nav>CONTENT<small>教材p.は紙面下部の通し番号です。PDF表示ページは2を加算。各図の証拠の採否と未確認部分を確認して使ってください。</small></main></html>'''.replace('NAV',nav).replace('CONTENT',''.join(entries))
    (OUT/'ここから図を見る.html').write_text(s,encoding='utf-8')
    (OUT/'編集方法.txt').write_text('''編集用の立証ピラミッドと関係図

最初に「ここから図を見る.html」を開くと、すべての図を一覧で見られます。

1 「05_立証ピラミッドと関係図.drawio」をdraw.io又はdiagrams.net対応エディターで開きます。
2 下部のページタブで、編集したい論点を選びます。
3 箱をドラッグすると位置を動かせます。文字は箱をダブルクリックして変更します。
4 接続線は箱同士に接続しています。線を選ぶと曲がり方や端点を変更できます。
5 線の説明もダブルクリックで変更できます。新しい線にも「認定」「推認」「条件」「反対」などの意味を付けてください。
6 ページを複製すれば、検察側と弁護側、実演前と実演後の版を分けて保存できます。
7 編集後は別名で保存すると、元の図を残せます。

色の意味
濃紺：要証事実又は検討対象。証明済みという意味ではありません。
青系：証拠に基づいて認定する事実。
灰色：証拠資料。
緑系：検察側の推認。
黄系：主張又は実演で確認が必要な内容。
赤系：反対事情・別の説明・限界。
紫系：人物又は場所。

矢印の意味
認定：証拠資料から事実を認める関係。
推認：事実を組み合わせ、別の事実や要証事実を考える関係。
条件：この確認がなければ推論を進められない関係。
反対：上位の推論を弱める又は限界を与える関係。
関係：人物・物・場所の関係。因果関係や有罪を示す意味ではありません。
時系列：前後関係。因果関係を示す意味ではありません。

PDFとSVGは閲覧・印刷用の書き出しです。draw.ioファイルを直しても自動では更新されません。エディターから再出力してください。
図の構造は「編集用/図の構造データ.json」、全ての接続関係は「編集用/ノードと矢印の一覧.txt」で確認できます。
教材の通しページとPDF表示ページは2ページずれています。甲3・乙2は採否留保のため、当日の実際の証言に合わせて更新してください。
''',encoding='utf-8-sig')
    old=ROOT/'ここから開く.html'
    if old.exists():
        content=old.read_text(encoding='utf-8')
        if '図解/ここから図を見る.html' not in content:
            insert='<h2>編集できる立証ピラミッドと関係図</h2><p><a href="図解/ここから図を見る.html">関係図をまとめて見る</a>　<a href="図解/05_立証ピラミッドと関係図.drawio">draw.io編集用</a>　<a href="図解/05_立証ピラミッドと関係図.pdf">図解のPDF</a></p>'
            content=content.replace('<h2>最初に使う資料</h2>',insert+'<h2>最初に使う資料</h2>');old.write_text(content,encoding='utf-8')

def main():
    for d in DIAGS:
        for n in d['nodes']:prepared_node(n)
        layout_labels(d)
    xml=drawio_file();pdf=render();export_text();index()
    print(json.dumps({'diagrams':len(DIAGS),'nodes':sum(len(d['nodes']) for d in DIAGS),'edges':sum(len(d['edges']) for d in DIAGS),'drawio':str(xml),'pdf':str(pdf)},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
