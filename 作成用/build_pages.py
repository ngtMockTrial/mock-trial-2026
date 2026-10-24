"""Build a self-contained, read-only GitHub Pages view from canonical notes."""
from __future__ import annotations

import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
from urllib.parse import quote, unquote, urlsplit

import markdown
import reasoning_graph as graph

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'https://github.com/ngtMockTrial/mock-trial-2026'
FIELDS = ('inputs', 'challenges', 'checks', 'preparation', 'potential_supports')
DETAIL_KINDS = {'確認課題', '準備資料', '供述獲得候補'}


class Renderer(HTMLParser):
    """Sanitize rendered Markdown and resolve vault-relative links for the web."""
    TAGS = set('p a strong em ul ol li h1 h2 h3 h4 h5 h6 pre code blockquote table thead tbody tr th td hr br img del'.split())

    def __init__(self, source, root, notes, documents, assets):
        super().__init__(convert_charrefs=False)
        self.source, self.root = source, root
        self.notes, self.documents, self.assets = notes, documents, assets
        self.parts = []

    def link(self, value):
        parsed = urlsplit(html.unescape(value))
        if parsed.scheme:
            return value if parsed.scheme.lower() in {'https', 'http'} else None
        if parsed.netloc:
            return None
        if not parsed.path:
            # Document heading links stay inside the current detail panel.
            return '#heading=' + quote(unquote(parsed.fragment), safe='')
        target = (self.source.parent / unquote(parsed.path)).resolve()
        if not target.is_relative_to(self.root.resolve()):
            return None
        relative = target.relative_to(self.root).as_posix()
        if relative in self.notes:
            return '#' + self.notes[relative]
        if relative in self.documents:
            anchor = '&heading=' + quote(unquote(parsed.fragment), safe='') if parsed.fragment else ''
            return '#doc=' + quote(relative, safe='') + anchor
        if target.is_file():
            self.assets.add(relative)
            return 'files/' + quote(relative, safe='/') + ('#' + parsed.fragment if parsed.fragment else '')
        return None

    def handle_starttag(self, tag, attrs):
        if tag not in self.TAGS:
            return
        attributes = dict(attrs)
        clean = []
        for key in ('title', 'alt', 'id'):
            if key in attributes:
                clean.append((key, attributes[key]))
        if tag in {'a', 'img'}:
            attribute = 'href' if tag == 'a' else 'src'
            value = self.link(attributes.get(attribute, ''))
            if value:
                clean.append((attribute, value))
                if value.startswith(('https://', 'http://')):
                    clean.append(('rel', 'noreferrer noopener'))
            if tag == 'img':
                clean.append(('loading', 'lazy'))
                if 'alt' not in attributes:
                    clean.append(('alt', '資料画像'))
        self.parts.append('<' + tag + ''.join(f' {k}="{html.escape(v or "", quote=True)}"' for k, v in clean) + '>')

    def handle_endtag(self, tag):
        if tag in self.TAGS and tag not in {'hr', 'br', 'img'}:
            self.parts.append('</' + tag + '>')

    def handle_data(self, data):
        self.parts.append(html.escape(data))

    def handle_entityref(self, name):
        self.parts.append('&' + name + ';')

    def handle_charref(self, name):
        self.parts.append('&#' + name + ';')


def render_body(body, source, root, notes, documents, assets):
    # Treat all source HTML as text; only Markdown-produced tags are admitted.
    body = html.escape(body, quote=False)
    def wiki(match):
        target, _, label = match[1].replace('\\|', '|').partition('|')
        label = label or target.rsplit('/', 1)[-1]
        target_path, _, anchor = target.partition('#')
        candidates = [root / target_path, root / (target_path + '.md'), source.parent / (target_path + '.md')]
        found = next((p for p in candidates if p.is_file()), None)
        if found:
            import os
            value = Path(os.path.relpath(found, source.parent)).as_posix()
            return '[' + label + '](' + quote(value, safe='/') + ('#' + quote(anchor, safe='') if anchor else '') + ')'
        return label
    body = re.sub(r'!?\[\[([^\]]+)\]\]', wiki, body)
    rendered = markdown.markdown(body, extensions=['tables', 'fenced_code', 'sane_lists', 'toc'])
    parser = Renderer(source, root, notes, documents, assets)
    parser.feed(rendered)
    return ''.join(parser.parts)


def make_payload(root=ROOT):
    notes = graph.load_notes(root)
    paths = {note['path'].relative_to(root).as_posix(): ident for ident, note in notes.items()}
    doc_paths = sorted((root / 'docs').rglob('*.md'))
    doc_paths += [root / name for name in ('README.md', 'AGENTS.md', 'CONTRIBUTING.md', 'CLAUDE.md', '検討/00_はじめに.md')]
    documents = {p.relative_to(root).as_posix(): p for p in doc_paths}
    assets, exported, docs, edges = set(), {}, {}, []
    for ident, note in notes.items():
        meta = note['meta']
        state, description = graph.availability(notes, ident)
        relative = note['path'].relative_to(root).as_posix()
        exported[ident] = dict(id=ident, title=meta['title'], kind=meta['kind'], side=meta['side'],
            status=meta['status'], review=meta['review'], reviewer=meta.get('reviewer', ''),
            reviewed_on=str(meta.get('reviewed_on', '')), state=state, availability=description,
            scope='detail' if meta['kind'] in DETAIL_KINDS else 'main',
            priority=meta.get('display_priority', 2), path=relative,
            html=render_body(note['body'], note['path'], root, paths, documents, assets),
            **{field: graph.refs(note, field) for field in FIELDS})
        for field in FIELDS:
            for other in graph.refs(note, field):
                source, target = (other, ident) if field in {'inputs', 'preparation'} else (ident, other)
                edges.append(dict(source=source, target=target, field=field))
    for relative, path in documents.items():
        body = path.read_text(encoding='utf-8-sig')
        title = re.search(r'^# (.+)', body, re.M)
        docs[relative] = dict(title=title[1] if title else path.stem, path=relative,
            html=render_body(body, path, root, paths, documents, assets))
    digest = hashlib.sha256(json.dumps(dict(notes=exported, edges=edges, documents=docs), ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return dict(notes=exported, edges=edges, documents=docs, repository=REPOSITORY, content_hash=digest), assets


def build(root=ROOT, destination=None):
    destination = destination or root / '_site'
    destination.mkdir(parents=True, exist_ok=True)
    payload, assets = make_payload(root)
    for name in ('index.html', 'styles.css', 'app.js'):
        shutil.copyfile(root / 'web' / name, destination / name)
    serialized = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    (destination / 'data.js').write_text('window.TRIAL_GRAPH=' + serialized + ';\n', encoding='utf-8')
    (destination / '.nojekyll').write_text('', encoding='utf-8')
    for relative in sorted(assets):
        target = destination / 'files' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / relative, target)
    print(f'Pages: {len(payload["notes"])} notes, {len(payload["edges"])} relations, {len(payload["documents"])} documents, {len(assets)} referenced files')
    return payload


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    build(destination=args.output)
