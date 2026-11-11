"""Export the prosecution draft and review material to editable Word files."""
from pathlib import Path
import argparse
import re
from docx import Document
from docx.shared import Mm, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.opc.constants import RELATIONSHIP_TYPE as RT

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output' / 'word'


def base(title, body_size=11):
    doc = Document()
    for node in list(doc.styles.element.iter(qn('w:pBdr'))):
        node.getparent().remove(node)
    section = doc.sections[0]
    section.page_width, section.page_height = Mm(210), Mm(297)
    section.top_margin = section.bottom_margin = Mm(22)
    section.left_margin = section.right_margin = Mm(23)
    section.footer_distance = Mm(10)
    for name in ['Normal', 'Title', 'Subtitle', 'Heading 1', 'Heading 2', 'Heading 3']:
        st = doc.styles[name]
        st.font.name = 'Yu Mincho' if name == 'Normal' else 'Yu Gothic'
        st.font.color.rgb = RGBColor(0, 0, 0)
        st.element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'), st.font.name)
        st.font.italic = False
        lang = OxmlElement('w:lang')
        lang.set(qn('w:val'), 'ja-JP')
        lang.set(qn('w:eastAsia'), 'ja-JP')
        st.element.get_or_add_rPr().append(lang)
        ppr = st.element.get_or_add_pPr()
        for tag, value in [('kinsoku', '1'), ('autoSpaceDE', '0'), ('autoSpaceDN', '0')]:
            child = OxmlElement('w:' + tag)
            child.set(qn('w:val'), value)
            ppr.append(child)
    normal = doc.styles['Normal']
    normal.font.size = Pt(body_size)
    normal.paragraph_format.line_spacing = Pt(body_size * 1.65)
    normal.paragraph_format.space_after = Pt(7)
    normal.paragraph_format.widow_control = True
    for name, size in [('Title', 20), ('Heading 1', 14), ('Heading 2', 12), ('Heading 3', 11)]:
        st = doc.styles[name]
        st.font.size = Pt(size)
        st.font.bold = True
        st.paragraph_format.space_before = Pt(12)
        st.paragraph_format.space_after = Pt(7)
        st.paragraph_format.keep_with_next = True
    doc.styles['Title'].paragraph_format.space_before = Pt(0)
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run()
    r.font.size = Pt(9)
    f = OxmlElement('w:fldSimple')
    f.set(qn('w:instr'), 'PAGE')
    r._r.addnext(f)
    doc.core_properties.title = title
    doc.core_properties.author = ''
    doc.core_properties.last_modified_by = ''
    doc.add_paragraph(title, 'Title')
    return doc


def inline(p, text, source_dir):
    # Native Word hyperlinks retain access to the original notes and PDFs.
    pieces = re.split(r'(\[[^\]]+\]\([^)]+\)|\*\*.*?\*\*|`[^`]+`)', text)
    for part in pieces:
        link = re.fullmatch(r'\[([^\]]+)\]\(([^)]+)\)', part)
        if link:
            label, target = link.groups()
            if not re.match(r'https?://', target):
                file, sep, fragment = target.partition('#')
                absolute = (source_dir / file).resolve()
                target = '../../' + absolute.relative_to(ROOT).as_posix()
                if sep:
                    target += '#' + fragment
            rel = p.part.relate_to(target, RT.HYPERLINK, is_external=True)
            h = OxmlElement('w:hyperlink')
            h.set(qn('r:id'), rel)
            r = OxmlElement('w:r')
            pr = OxmlElement('w:rPr')
            color = OxmlElement('w:color')
            color.set(qn('w:val'), '000000')
            pr.append(color)
            r.append(pr)
            t = OxmlElement('w:t')
            t.text = label
            r.append(t)
            h.append(r)
            p._p.append(h)
        elif part.startswith('**') and part.endswith('**'):
            p.add_run(part[2:-2]).bold = True
        elif part.startswith('`') and part.endswith('`'):
            p.add_run(part[1:-1])
        else:
            p.add_run(part)


def prose(doc, text, source_dir, style=None):
    p = doc.add_paragraph(style=style)
    inline(p, text, source_dir)
    return p


def convert_review(doc, source):
    lines = source.read_text(encoding='utf-8').splitlines()
    i = 1  # title already provided by the destination document
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('変更記録：'):
            break  # Repository work history stays in the source notes.
        if not line or line == '---':
            i += 1
            continue
        if line.startswith('|'):
            headers = [s.strip() for s in line.strip('|').split('|')]
            i += 2
            while i < len(lines) and lines[i].strip().startswith('|'):
                values = [s.strip() for s in lines[i].strip().strip('|').split('|')]
                # Each record is a short section, avoiding cramped multi-page table cells.
                prose(doc, values[0], source.parent, 'Heading 3')
                for label, value in zip(headers[1:], values[1:]):
                    prose(doc, '**' + label + '**　' + value, source.parent)
                i += 1
            continue
        if line.startswith('#'):
            n = len(line) - len(line.lstrip('#'))
            title = re.sub(r'[：・／（）]', ' ', line.lstrip('#').strip())
            prose(doc, title, source.parent, 'Heading ' + str(min(n - 1, 3)))
        else:
            line = re.sub(r'^- ', '', line)
            prose(doc, line, source.parent)
        i += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--suffix', default='', help='Save a separate revision without overwriting open Word files')
    suffix = parser.parse_args().suffix
    OUT.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'docs/25_論告案_実回答反映.md'
    text = source.read_text(encoding='utf-8')
    parts = text.split('\n---\n')
    body = parts[1]
    draft = base('論告', body_size=12)
    draft.styles['Normal'].paragraph_format.space_after = Pt(4)
    draft.styles['Normal'].paragraph_format.line_spacing = Pt(19)
    draft.add_paragraph('学校名：　　　　　　　　　発表者名：　　　　　　　　　')
    p = draft.add_paragraph('木村忠太被告事件　12分用　人の確認前の案')
    p.style = draft.styles['Subtitle']
    p.runs[0].font.size = Pt(10)
    p = draft.add_paragraph('甲3・乙2の使用は共有された大会運用が認められることが条件です。使用前に別冊の根拠と使用条件を確認してください。見出しとP番号は読み上げず、冒頭で発表者名を名乗ってください。')
    p.paragraph_format.line_spacing = Pt(15)
    for run in p.runs:
        run.font.size = Pt(9)
    expected = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('##'):
            title = line.lstrip('#').strip()
            prose(draft, title, source.parent, 'Heading 2' if line.startswith('###') else 'Heading 1')
        else:
            m = re.match(r'〔(P\d+[a-z]?)〕(.*)', line)
            assert m, line
            expected.append(m.group(2))
            p = draft.add_paragraph()
            r = p.add_run(m.group(1) + '　')
            r.font.size = Pt(8)
            r.font.color.rgb = RGBColor(90, 90, 90)
            p.add_run(m.group(2))
    draft_path = OUT / ('木村忠太被告事件_論告案' + suffix + '.docx')
    draft.save(draft_path)
    reread = Document(draft_path)
    actual = [re.sub(r'^P\d+[a-z]?　', '', p.text) for p in reread.paragraphs if re.match(r'^P\d+[a-z]?　', p.text)]
    assert actual == expected, 'Draft content differs from the source'
    assert len(actual) == 29

    review = base('木村忠太被告事件 論告の根拠と使用条件')
    review.add_paragraph('論告案のP番号に対応する確認資料　Word版作成 2026年11月10日')
    convert_review(review, ROOT / 'docs/26_論告案の根拠と使用条件.md')
    prose(review, '追加論告教材の確認と利用', source.parent, 'Heading 1')
    convert_review(review, ROOT / 'docs/27_追加論告教材の確認と利用.md')
    review_path = OUT / ('木村忠太被告事件_根拠と使用条件' + suffix + '.docx')
    review.save(review_path)
    print('Created:', draft_path)
    print('Created:', review_path)
    print('Verified: 29 draft paragraphs match the source exactly')


if __name__ == '__main__':
    main()
