"""Ensure publication preserves relationships and safely renders source text."""
import hashlib
from pathlib import Path
import tempfile
import unittest

import build_pages as pages
import reasoning_graph as graph


class PagesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload, cls.assets = pages.make_payload()

    def test_published_graph_matches_canonical_relations_and_status(self):
        notes = graph.load_notes()
        self.assertEqual(set(self.payload['notes']), set(notes))
        actual = {(e['source'], e['target'], e['field']) for e in self.payload['edges']}
        expected = set()
        for ident, note in notes.items():
            for field in pages.FIELDS:
                for other in graph.refs(note, field):
                    source, target = (other, ident) if field in {'inputs', 'preparation'} else (ident, other)
                    expected.add((source, target, field))
        self.assertEqual(actual, expected)
        for ident, note in notes.items():
            for field in ('review', 'status', 'kind', 'side'):
                self.assertEqual(self.payload['notes'][ident][field], note['meta'][field])
        self.assertFalse(any(e['source'] in {'W01', 'W02'} and e['field'] == 'inputs' for e in self.payload['edges']))

    def test_note_links_and_original_page_anchor_work_on_pages(self):
        notes = graph.load_notes()
        paths = {n['path'].relative_to(pages.ROOT).as_posix(): i for i, n in notes.items()}
        result = pages.render_body('[[検討/ノート/F03|前提]]\n\n[原本](../../00_元資料/教材集.pdf#page=23)',
                                   notes['R01']['path'], pages.ROOT, paths, {}, set())
        self.assertIn('href="#F03"', result)
        self.assertIn('#page=23', result)
        self.assertIn('href="files/', result)

    def test_raw_html_and_unsafe_links_are_not_executable(self):
        result = pages.render_body('<script>alert(1)</script>\n\n[危険](javascript:alert)\n\n[外部](https://example.com)',
                                   pages.ROOT / 'README.md', pages.ROOT, {}, {}, set())
        self.assertNotIn('<script', result)
        self.assertNotIn('href="javascript:', result)
        self.assertIn('href="https://example.com"', result)
        self.assertIn('&lt;script&gt;', result)

    def test_build_copies_only_referenced_files_and_never_changes_sources(self):
        originals = {p: hashlib.sha256(p.read_bytes()).digest() for p in (pages.ROOT / '00_元資料').rglob('*') if p.is_file()}
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            pages.build(destination=destination)
            self.assertTrue((destination / 'index.html').is_file())
            self.assertTrue((destination / 'data.js').is_file())
            self.assertTrue((destination / 'vendor/d3-force.min.js').is_file())
            self.assertTrue((destination / 'vendor/d3-force.LICENSE').is_file())
            self.assertFalse((destination / '.obsidian').exists())
            self.assertFalse((destination / '.git').exists())
            for relative in self.assets:
                self.assertEqual((destination / 'files' / relative).read_bytes(), (pages.ROOT / relative).read_bytes())
        self.assertEqual(originals, {p: hashlib.sha256(p.read_bytes()).digest() for p in originals})

    def test_graph_settings_are_shared_from_a_validated_snapshot(self):
        import json
        from export_graph_settings import validate_settings
        snapshot = json.loads((pages.ROOT / 'web/graph-settings.json').read_text(encoding='utf-8'))
        self.assertEqual(self.payload['graph_settings'], snapshot)
        invalid = {**snapshot['options'], 'centerStrength': float('nan')}
        with self.assertRaises(ValueError):
            validate_settings(invalid)

    def test_settings_capture_does_not_write_personal_config_or_pins(self):
        import json
        from export_graph_settings import capture
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / '.obsidian/graph.json'
            config.parent.mkdir()
            options = {**self.payload['graph_settings']['options'], 'centerStrength': .23, 'pinNodes': {'private': {'x':1}}}
            config.write_text(json.dumps(options), encoding='utf-8')
            before = config.read_bytes()
            snapshot = capture(root)
            self.assertEqual(config.read_bytes(), before)
            self.assertEqual(snapshot['options']['centerStrength'], .23)
            self.assertNotIn('pinNodes', snapshot['options'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
