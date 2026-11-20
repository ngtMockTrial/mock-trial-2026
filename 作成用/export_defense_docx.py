"""Export the defense closing argument with the shared Word formatting helpers."""
import re
from docx import Document
from docx.shared import Pt, RGBColor
from export_prosecution_docx import ROOT, OUT, base, prose, convert_review


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'docs/28_弁護人最終弁論案.md'
    text = source.read_text(encoding='utf-8').split('\n---\n')[1]
    doc = base('最終弁論', body_size=12)
    doc.add_paragraph('学校名：　　　　　　　　　発表者名：　　　　　　　　　')
    p = doc.add_paragraph('木村忠太被告事件　弁護側　12分用　人の確認前の案')
    for r in p.runs:
        r.font.size = Pt(10)
    p = doc.add_paragraph('甲3・乙2の使用は共有された大会運用が認められることが条件です。見出し・B番号は読み上げず、使用前に別冊の根拠と使用条件を確認してください。')
    p.paragraph_format.line_spacing = Pt(15)
    for r in p.runs:
        r.font.size = Pt(9)
    expected = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('##'):
            prose(doc, line.lstrip('#').strip(), source.parent,
                  'Heading 2' if line.startswith('###') else 'Heading 1')
        else:
            m = re.fullmatch(r'〔(B\d+)〕(.*)', line)
            assert m
            expected.append(m.group(2))
            p = doc.add_paragraph()
            r = p.add_run(m.group(1) + '　')
            r.font.size = Pt(8)
            r.font.color.rgb = RGBColor(90, 90, 90)
            p.add_run(m.group(2))
    path = OUT / '木村忠太被告事件_弁護人最終弁論案.docx'
    doc.save(path)
    actual = [re.sub(r'^B\d+　', '', p.text) for p in Document(path).paragraphs
              if re.match(r'^B\d+　', p.text)]
    assert len(expected) == 28 and actual == expected
    support = base('最終弁論の根拠と使用条件')
    convert_review(support, ROOT / 'docs/29_最終弁論の根拠と使用条件.md')
    support.save(OUT / '木村忠太被告事件_最終弁論の根拠と使用条件.docx')
    print('Verified 28 paragraphs; body characters:', sum(map(len, expected)))


if __name__ == '__main__':
    main()
