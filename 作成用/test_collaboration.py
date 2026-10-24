"""Regression tests for source protection and participant settings."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from setup_collaborator import setup
from verify_repository import check_links, check_originals


class CollaborationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_setup_preserves_existing_preferences_and_adds_missing_files(self):
        source = self.root / '作成用/obsidian初期設定'
        source.mkdir(parents=True)
        (source / 'graph.json').write_text('{"default":true}', encoding='utf-8')
        (source / 'bookmarks.json').write_text('{"items":[]}', encoding='utf-8')
        target = self.root / '.obsidian'
        target.mkdir()
        (target / 'graph.json').write_bytes(b'human preferences')
        self.assertEqual(setup(self.root), ['bookmarks.json'])
        self.assertEqual((target / 'graph.json').read_bytes(), b'human preferences')
        self.assertEqual(setup(self.root), [])

    def test_original_change_and_unregistered_addition_are_rejected(self):
        ledger = self.root / 'docs/原文/原資料ハッシュ一覧.md'
        ledger.parent.mkdir(parents=True)
        originals = self.root / '00_元資料'
        originals.mkdir()
        rows = []
        for index in range(15):
            name = f'{index}.bin'
            data = bytes([index])
            (originals / name).write_bytes(data)
            rows.append(f'| [{name}](../../00_元資料/{name}) | `{hashlib.sha256(data).hexdigest()}` |')
        ledger.write_text('\n'.join(rows), encoding='utf-8')
        self.assertEqual(check_originals(self.root), 15)
        (originals / '0.bin').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, '欠落または変更'):
            check_originals(self.root)
        (originals / '0.bin').write_bytes(bytes([0]))
        (originals / 'extra.bin').write_bytes(b'new')
        with self.assertRaisesRegex(ValueError, '登録が一致'):
            check_originals(self.root)

    def test_missing_links_fail_but_external_links_and_code_examples_do_not(self):
        docs = self.root / 'docs'
        docs.mkdir()
        for name in ['README.md', 'AGENTS.md', 'CLAUDE.md']:
            (self.root / name).write_text('', encoding='utf-8')
        page = docs / 'test.md'
        page.write_text('[link](https://example.com)\n```md\n[example](missing.md)\n```\n', encoding='utf-8')
        check_links(self.root)
        page.write_text('[broken](missing.md)', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'リンク切れ'):
            check_links(self.root)


if __name__ == '__main__':
    unittest.main(verbosity=2)
