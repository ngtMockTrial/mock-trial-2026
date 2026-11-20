"""事件知識の全項目と甲1見取図を、場所別の概観と詳細年表に組む。"""
import json
import os
from pathlib import Path
import subprocess

from PIL import Image
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.lib.textsplit import wordSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/知識/事件知識.json"
OUT = ROOT / "output/pdf"
PDF = OUT / "事件の場所別時系列図.pdf"
PREVIEW = OUT / "事件全体の時系列"
W, H = landscape(A4)
M = 32
INK, MUTED, LINE = "#172D31", "#485F62", "#C7D5D1"
TEAL, PLUM, AMBER = "#006A60", "#654A76", "#865315"
PALE, WHITE = "#F1F6F3", "#FFFFFF"
REG, BOLD, SERIF = "TimelineJP", "TimelineJP-Bold", "TimelineJP-Serif"

# 各項目の日時・本文・根拠・限界は台帳から読む。未確定時刻は帯として扱う。
# (見出し、期間、K番号、欄外に残す原資料の補足)
SECTIONS = [
    ("木村と岸井の接点、眼鏡の購入、本所との別れ", "事件前  ／  高校時代から2025年10月25日まで", [1, 2, 3, 4, 5, 6],
     "検察官の冒頭陳述は、木村と本所が2022年夏頃に交際を始めたとする（教材p.32）。10月25日の別れのやり取りは甲2に残る。"),
    ("別れた後の連絡と、12月24日のメッセージ", "事件前  ／  2025年10月26日から12月24日まで", [7, 8, 9, 10, 11, 12],
     "木村は岸井への怒りを認め、殺したい気持ちはなかったと回答した。駐車場の利用を知っていたという木主44と、利用自体が分からないとの木主45末尾が並ぶ（S04 p.15〜16）。"),
    ("木村の忘年会と帰宅、大滝の巡回開始", "事件当日  ／  2025年12月26日・午前から午後", list(range(13, 21)),
     "採否留保の甲3には、大滝が朝に高知市北元町の事務所で朝礼・報告書作成後、南国市の1か所目に12時頃、土佐市に15時頃到着したとの記載がある（教材p.20〜21）。"),
    ("大滝は巡回を続け、木村は自宅で過ごしたと説明", "事件当日  ／  12月26日・15時40分頃から18時過ぎ頃", [21, 22, 23, 25, 24, 26, 27],
     "2か所目の故障対応が終わった時刻、3か所目を出た時刻、4か所目に着いた時刻は、いずれも大滝の記憶による概数。"),
    ("駐車場での清掃から、大滝の退勤まで", "事件当日  ／  12月26日・18時過ぎ頃から退勤後", list(range(28, 37)),
     "K028〜K033は同じ清掃についての説明。大滝は拾得物を会社に報告し、落とし主が現れなければ警察に届ける決まりだと答えた（S04 p.5／大主33）。"),
    ("木村の就寝、起訴状の時刻、コンビニ前の映像", "事件当日  ／  12月26日・19時30分頃から21時頃", list(range(37, 42)),
     "検察官は刺突後に自転車でコンビニ前を通り帰宅したと主張。弁護人は木村が自宅で寝ており、眼鏡に血液が付いたのは昼に落とした後だと主張する（双方の冒頭陳述、教材p.33〜34）。"),
    ("駐車場での通報から、病院での死亡確認へ", "事件当日  ／  12月26日・20時45分頃から死亡後", list(range(42, 47)),
     "Aは大林が岸井を発見した位置、Bは警察官が眼鏡を見つけた位置。刺突の正確な位置・時刻と、眼鏡の落下・血液付着の時刻は特定されていない（甲1 教材p.3〜6・11・14）。"),
    ("眼鏡を捜したという説明と、警察の訪問", "事件後  ／  2025年12月27日から2026年1月5日まで", list(range(47, 53)),
     "警察は眼鏡のつるのロゴから製造元に照会し、正規販売店を確認。店が提出した購入者2名の商品引取証に住所があり、木村宅を訪れた（甲1 教材p.4）。"),
    ("眼鏡・自転車の鑑定、現場撮影と逮捕", "捜査  ／  鑑定・照会の日は不明。撮影・逮捕は2026年1月6日・9日。", [53, 54, 55, 56, 57],
     "甲1は自転車の指紋一致を1月9日の逮捕に至った事情として記す。個々の鑑定日や、現場で血液・指紋が付いた時刻の記載はない（教材p.4〜5）。"),
    ("調書の作成、公訴提起、尋問記録の受領", "手続・資料の履歴  ／  2026年1月10日から11月9日まで", list(range(58, 65)),
     "教材p.2の証拠整理メモでは甲1・甲2・乙1、大滝証人を採用し、甲3・乙2は採否留保。S04の実演日は不明。受領日と、各回答が述べる出来事の日は別々に読む。"),
]


def box(c, x, y, w, h, color):
    c.setFillColor(HexColor(color))
    c.rect(x, H - y - h, w, h, fill=1, stroke=0)


def rule(c, x, y, end_x, end_y, color=LINE, width=0.6):
    c.setStrokeColor(HexColor(color))
    c.setLineWidth(width)
    c.line(x, H - y, end_x, H - end_y)


def label(c, x, y, value, size=10, font=REG, color=INK):
    c.setFillColor(HexColor(color))
    c.setFont(font, size)
    c.drawString(x, H - y - size, value)


def lines(value, width, size, font=REG):
    return [line for para in value.splitlines() for _, line in wordSplit(para, width, font, size)]


def paragraph(c, x, y, value, width, size=10, leading=14, font=REG, color=INK):
    for entry in lines(value, width, size, font):
        label(c, x, y, entry, size, font, color)
        y += leading
    return y


def header(c, section, title, subtitle, key, bookmark):
    c.bookmarkPage(key)
    c.addOutlineEntry(bookmark, key)
    box(c, 0, 0, W, 5, TEAL)
    label(c, M, 16, "木村忠太被告事件   ／   場所別時系列図", 9, BOLD, TEAL)
    label(c, W - M - pdfmetrics.stringWidth(section, REG, 9), 16, section, 9, REG, MUTED)
    label(c, M, 33, title, 23, SERIF)
    label(c, M, 72, subtitle, 10, REG, MUTED)


def footer(c):
    rule(c, M, H - 30, W - M, H - 30)
    label(c, M, H - 24, "教材p.N → PDF表示 N＋2ページ  ／  S04＝実際の尋問・質問記録（PDF表示どおり）  ／  大＝大滝、木＝木村、主＝主尋問・主質問、反＝反対尋問・反対質問  ／  AI整理・未レビュー", 8, REG, MUTED)
    page = f"{c.getPageNumber()}  /  {len(SECTIONS) + 3}"
    label(c, W - M - pdfmetrics.stringWidth(page, BOLD, 9), H - 25, page, 9, BOLD, TEAL)
    c.showPage()


def jump(c, x, y, w, h, key):
    c.linkRect("", key, (x, H - y - h, x + w, H - y), relative=0, thickness=0)


def case_overview(c):
    header(c, "全体を一枚で見る", "木村忠太被告事件の時系列",
           "岸井新之助が発見された2025年12月26日を中心に、左から事件前・当日・事件後の順に読む。各欄から出典付きの詳細へ進めます。",
           "case", "事件前から捜査・資料受領まで")
    periods = [
        ("事件前", "高校時代〜12月24日", [
            ("高校時代・同窓会", "五万十工業高校", "木村は、岸井と同級生で、卒業後の同窓会で少し話したと説明。", 1),
            ("10月11日", "ランドルト高知店", "木村が眼鏡を購入。同型は12月26日までに同店で2点売れた。", 4),
            ("10月13日・25日", "本所と木村のLINE", "本所マサミが木村の飲酒や紛失を注意。25日、別れを告げた。", 6),
            ("10月26日〜11月5日", "木村から本所へのLINE", "木村が復縁や連絡を求める。本所宅を2度訪ねたとも説明しているが、訪問日は不明。", 7),
            ("12月24日", "知人との電話／本所へのLINE", "木村は交際の話を聞いたと説明。本所へのLINEに岸井への怒りを記す。", 11),
        ]),
        ("事件当日", "12月26日・高知市", [
            ("昼〜14時頃", "五哲駅西口・帰り道", "木村は忘年会後に歩いて帰宅し、駐車場の横で転んだと説明。眼鏡の落下は本人の推測。", 18),
            ("18時過ぎ頃", "本件駐車場", "管理担当の大滝悟郎が清掃。眼鏡を見なかったと証言。急いで通りながら見たとも回答。", 31),
            ("20時30分頃", "駐車場・周辺／木村宅", "起訴状は木村が刺したと主張。木村は在宅を述べ、就寝は20時30分頃か21時頃と説明。", 40),
            ("20時32分頃", "駐車場入口の南約200m", "コンビニの映像に自転車で南へ走る男性。顔は判別できず、人物・車両とも未特定。", 41),
            ("20時45分頃〜21時頃", "本件駐車場・A地点とB地点", "大林銀弥がAで岸井を発見し110番。警察が呼吸を確認し、Bで血痕付き眼鏡を発見。", 42),
            ("21時55分", "五哲大学病院", "搬送先で岸井の死亡を確認。死因は刺創による出血性ショック。", 45),
        ]),
        ("事件後", "翌朝〜2026年11月", [
            ("12月27日朝", "木村宅・駐車場付近", "木村は眼鏡の紛失に気付き、捜したと説明。捜索範囲は尋問記録と乙2で異なる。", 48),
            ("1月5日", "ハイツ京極・木村宅と駐輪場", "木村が眼鏡を自分の物と認める。警察は駐輪場で血痕付きの共用自転車を発見。", 52),
            ("鑑定日不明", "押収した自転車・領置した眼鏡", "どちらの血痕も岸井のDNA型と一致。木村の指紋も検出。付着時刻は不明。", 53),
            ("1月9日・30日", "逮捕・高知地裁への起訴", "9日14時頃に木村を逮捕。30日、検察官が殺人として公訴提起。", 62),
            ("4月15日・11月9日", "捜査報告書・尋問記録", "4月に甲1作成。11月に大滝・木村の実際の回答記録を受領。尋問の実施日は不明。", 64),
        ]),
    ]
    gap = 13
    width = (W - 2 * M - 2 * gap) / 3
    for col, (name, period, stops) in enumerate(periods):
        x = M + col * (width + gap)
        box(c, x, 98, width, 34, INK if col == 1 else "#E1ECE7")
        heading = WHITE if col == 1 else INK
        label(c, x + 10, 104, name, 14, BOLD, heading)
        label(c, x + 82, 108, period, 9, REG, heading)
        top = 145
        step = 67 if col == 1 else 79
        rule(c, x + 5, top + 7, x + 5, top + 7 + (len(stops) - 1) * step, "#A2BCB4", 1.35)
        for n, (time, place, body, target) in enumerate(stops):
            y = top + n * step
            c.setFillColor(HexColor(TEAL))
            c.circle(x + 5, H - y - 7, 3.4, stroke=0, fill=1)
            label(c, x + 14, y - 2, time, 11.3, BOLD)
            label(c, x + 14, y + 14, place, 9.1, BOLD, TEAL)
            end = paragraph(c, x + 14, y + 28, body, width - 18, 9.8, 12.6)
            if end > y + step + 1:
                raise ValueError(f"概観が次の項目に重なります: {time}")
            jump(c, x + 10, y - 3, width - 10, step, f"K{target:03}")
    label(c, M, 543, "2ページ　当日の場所別時系列　　　　3ページ　現場の見取図　　　　4ページ以降　詳細年表 K001〜K064・出典・未確認点", 9.3, BOLD, TEAL)
    jump(c, M, 538, 152, 23, "overview")
    jump(c, M + 161, 538, 133, 23, "maps")
    jump(c, M + 294, 538, 372, 23, "K001")
    footer(c)


# 色と文字の両方で記録の種類を表示する。一つのセルは一つの根拠に結ぶ。
NIGHT = [
    ("正午〜\n14時台", ("木村の説明", "駅西口で忘年会。駐車場の横を歩いて帰宅。転倒時に眼鏡を落とした可能性を述べた。", 17),
     None, ("甲1・店舗", "14時頃、木村が「なんちゃっ亭」を訪れていたことを捜査で確認。", 16)),
    ("17〜18時台", ("木村の説明", "自宅で17時頃に起き、テレビを見て18時頃にラーメンを食べた。", 25),
     ("大滝の説明", "18時過ぎ頃に清掃。眼鏡は見なかった。急いで通りながら全体を見たとも回答。", 31),
     ("甲1・高知市／大滝の勤務先", "17時04分、高知市で日没。18時50分、大滝が退勤（タイムカード）。", 35)),
    ("19時30分頃", ("木村の説明", "自宅でシャワーを浴び、上下黒いスウェットに着替えた。", 37), None, None),
    ("20時30分頃", ("木村の説明", "自宅で就寝したと説明。主質問では20時30分頃、反対質問では21時かもしれないと回答。", 38),
     ("起訴状の主張", "木村が駐車場の敷地内または周辺で岸井を刃物で刺したとする。", 40), None),
    ("20時32分頃", None, None, ("甲1・コンビニ前", "駐車場入口の南約200m。黒いダウンの男性が自転車で北から南へ通過。顔は判別不能。", 41)),
    ("20時45分頃\n〜21時頃", None, ("甲1・発見と通報", "20時45分頃、大林がAで岸井を発見し110番。50分頃、警察が呼吸を確認。21時頃、Bで血痕付き眼鏡を発見。", 42), None),
    ("21時55分", None, None, ("甲1・五哲大学病院", "救急搬送された岸井の死亡を確認。検案による死因は刺創による出血性ショック。", 45)),
]


def overview(c):
    header(c, "事件当日の概観", "12月26日、どこで何が起きたか",
           "2025年12月26日（金）  ／  左端の時刻を下へたどる。同じ行は同じ時間帯。空欄は、この図に対応する記録がない箇所。", "overview", "事件当日の場所別時系列")
    xs = [M, 116, 346, 576, W - M]
    box(c, M, 97, W - 2 * M, 26, INK)
    for x, name in zip(xs, ("時刻", "店・帰り道・木村宅", "本件駐車場・その周辺", "市内の各地点・病院")):
        label(c, x + 8, 103, name, 10.5, BOLD, WHITE)
    y = 123
    for index, (time, *cells) in enumerate(NIGHT):
        h = (59, 62, 48, 57, 57, 69, 55)[index]
        box(c, M, y, W - M * 2, h, WHITE if index % 2 == 0 else PALE)
        box(c, M, y, xs[1] - M, h, "#E8F0ED")
        paragraph(c, M + 8, y + 8, time, 78, 10.5, 16, BOLD)
        for col, cell in enumerate(cells, 1):
            x = xs[col]
            rule(c, x, y, x, y + h)
            if cell is None:
                continue
            kind, content, number = cell
            color = PLUM if "説明" in kind else AMBER if "主張" in kind else TEAL
            label(c, x + 8, y + 4, kind, 8.5, BOLD, color)
            end = paragraph(c, x + 8, y + 18, content, xs[col + 1] - x - 16, 10.1, 13.1)
            if end > y + h + 2:
                raise ValueError(f"概観のセルが超過: {kind}")
            jump(c, x, y, xs[col + 1] - x, h, f"K{number:03}")
        rule(c, M, y + h, W - M, y + h)
        y += h
    label(c, M, y + 7, "場所は次ページの見取図へ。各欄を押すと、該当する時間帯の出典と記録上の限界を読めます。", 9, REG, MUTED)
    jump(c, M, y + 4, 120, 18, "maps")
    footer(c)


def maps(c):
    header(c, "現場見取図  ／  甲1", "駅・駐車場・コンビニ・自宅の位置",
           "本件駐車場は高知市五哲町5-31の「パーク on it Hey！」。両図とも上が北。AとBは12月26日夜の発見位置を表す。", "maps", "現場見取図と発見位置")
    source = ROOT / "作成用/確認用/pdfs/教材集"
    for n, crop, x, y, w, h in [
        (15, (128, 195, 701, 1020), M, 125, 224, 385),
        (16, (145, 290, 719, 852), 280, 125, 261, 278),
    ]:
        with Image.open(source / f"page-{n}.png") as im:
            pic = im.crop(crop)
            scale = min(w / pic.width, h / pic.height)
            dw, dh = pic.width * scale, pic.height * scale
            c.drawImage(ImageReader(pic), x, H - y - dh, dw, dh)
    label(c, M, 98, "現場周辺", 13, BOLD, TEAL)
    label(c, 280, 98, "駐車場の内部", 13, BOLD, TEAL)
    label(c, 567, 98, "地図と時刻を照合する", 13, BOLD, TEAL)
    paragraph(c, M, 464, "甲1・見取図1（教材p.13）。赤い白抜きの丸は街灯の位置。", 218, 9, 14, REG, MUTED)
    paragraph(c, 280, 404, "甲1・見取図2（教材p.14）。東側と南側に出入口がある。場内の赤い白抜きの丸は照明。", 258, 9, 14, REG, MUTED)
    paragraph(c, 280, 460, "写真⑤ではA・Bの区画に当日契約はなく、その右隣が岸井の契約区画（甲1 教材p.6・11）。", 258, 10, 15)
    for y, tag, detail in [
        (130, "昼  ／  店からの帰り道", "木村は五哲駅西口の店から駐車場の横を歩いて帰ったと説明。木主12の図示はS04に未収録で、道順や転倒地点は特定できない。"),
        (229, "20時32分頃  ／  コンビニ前", "駐車場は木村宅の北約400m。コンビニは駐車場入口の南約200m、木村宅の北約200m。映像で分かるのは店前での南向きの走行まで。"),
        (337, "20時45分頃  ／  A地点", "駐車に来た大林銀弥が岸井新之助を発見。大滝悟郎は夕方に清掃した管理担当者。"),
        (421, "21時頃  ／  B地点", "警察官が血痕付き眼鏡を発見・領置。落ちた時刻、Bに来た経緯、血液が付いた時刻は不明。"),
    ]:
        rule(c, 567, y - 4, W - M, y - 4)
        label(c, 567, y, tag, 11, BOLD, TEAL)
        paragraph(c, 567, y + 21, detail, W - M - 567, 10.5, 15)
    paragraph(c, M, 531, "出典　甲1 教材p.3〜6・10〜14、S04 p.11・13・16／木主12〜15・26、木反3。距離は甲1本文の概数。", W - 2 * M, 9, 13, REG, MUTED)
    footer(c)


def detail(c, entries, section):
    title, period, numbers, note = section
    rows = [entries[f"K{n:03}"] for n in numbers]
    header(c, "詳細年表  ／  記録とその出典", title, period, "sec" + rows[0]["id"], title)
    box(c, M, 95, W - 2 * M, 24, INK)
    for x, name in [(M + 9, "いつ・どこで"), (239, "誰が・何をしたか"), (573, "その記録から言える範囲")]:
        label(c, x, 100, name, 10, BOLD, WHITE)
    y = 119
    note_lines = lines(note, W - 2 * M - 89, 9)
    note_y = H - 42 - max(29, 9 + 13 * len(note_lines))
    # 各行は実測した行数に合わせる。余白は少数行のページでも引き延ばさない。
    layouts = []
    for row in rows:
        stamp = row["time_text"].removeprefix("2025-12-26 ").replace("同上", "18時過ぎ頃の清掃")
        where = row["place"]
        statement = row["statement"]
        source = "、".join(dict.fromkeys(ref["locator"] for ref in row["source_refs"]))
        locators = row["subject"] + "　／　" + source
        a = 13 * len(lines(stamp, 186, 10.2, BOLD)) + 12 * len(lines(where, 186, 9.6))
        b = 13 * len(lines(statement, 315, 10.2)) + 10.5 * len(lines(locators, 315, 8))
        d = 12.4 * len(lines(row["limitations"], 225, 9.4)) + 10.5 * len(lines(row["classification"], 190, 8, BOLD))
        layouts.append((stamp, where, statement, locators, max(a, b, d) + 9))
    padding = min(11, (note_y - y - 6 - sum(layout[-1] for layout in layouts)) / len(rows))
    if padding < 0:
        raise ValueError(f"詳細年表がページを超過: {title} ({padding:.1f})")
    for index, (row, layout) in enumerate(zip(rows, layouts)):
        stamp, where, statement, locators, height = layout
        height += padding
        box(c, M, y, W - 2 * M, height, WHITE if index % 2 == 0 else PALE)
        # 目次・概観から該当項目の掲載ページを開ける。
        c.bookmarkPage(row["id"])
        top = y + 4
        end = paragraph(c, M + 9, top, stamp, 186, 10.2, 13, BOLD)
        paragraph(c, M + 9, end + 1, where, 186, 9.6, 12, REG, TEAL)
        end = paragraph(c, 239, top, statement, 315, 10.2, 13)
        paragraph(c, 239, end + 1, locators, 315, 8, 10.5, REG, MUTED)
        kind = row["classification"]
        color = AMBER if "主張" in kind else PLUM if "供述記録" in kind else TEAL
        label(c, 573, top, row["id"], 8, BOLD, MUTED)
        end = paragraph(c, 606, top, kind, 190, 8, 10.5, BOLD, color)
        paragraph(c, 573, end + 1, row["limitations"], 225, 9.4, 12.4)
        y += height
        rule(c, M, y, W - M, y)
    box(c, M, note_y, W - M * 2, H - 40 - note_y, "#E7F0EB")
    label(c, M + 8, note_y + 6, "資料を読む補足", 9, BOLD, TEAL)
    paragraph(c, M + 81, note_y + 6, note, W - 2 * M - 89, 9, 13)
    footer(c)


def main():
    fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    for name, file in [(REG, "meiryo.ttc"), (BOLD, "meiryob.ttc"), (SERIF, "yumindb.ttf")]:
        pdfmetrics.registerFont(TTFont(name, str(fonts / file)))
    data = json.loads(DATA.read_text(encoding="utf-8"))
    entries = {r["id"]: r for r in data["chronology"]}
    scheduled = [f"K{n:03}" for section in SECTIONS for n in section[2]]
    if sorted(scheduled) != sorted(r["id"] for r in data["chronology"]) or len(entries) != len(scheduled):
        raise ValueError("年表のIDに欠落か重複があります。場所・掲載先を確認してください。")
    OUT.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(PDF), pagesize=(W, H), pageCompression=1, invariant=1)
    c.setTitle("木村忠太被告事件　事件の場所別時系列図")
    c.setAuthor("模擬裁判資料整理")
    case_overview(c)
    overview(c)
    maps(c)
    for section in SECTIONS:
        detail(c, entries, section)
    c.save()
    subprocess.run(["pdftoppm", "-f", "1", "-l", "1", "-singlefile", "-r", "150",
                    "-png", str(PDF), str(PREVIEW)], check=True)


if __name__ == "__main__":
    main()
