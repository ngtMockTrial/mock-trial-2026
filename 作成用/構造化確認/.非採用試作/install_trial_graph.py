"""明示的な初回導入・プラグイン更新用。通常の検討更新からは設定を書き換えない。"""
import json
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
source=Path(__file__).with_name('trial-graph')
dest=ROOT/'.obsidian/plugins/mock-trial-graph'
dest.mkdir(parents=True,exist_ok=True)
for name in ['view.js','styles.css','manifest.json']:
    shutil.copyfile(source/name,dest/name)
# Obsidianのプラグインローダーは単一main.jsを評価するため、相対requireを残さない。
bundle=(source/'view.js').read_text(encoding='utf-8')+'\n'+(source/'main.js').read_text(encoding='utf-8').replace("const {mount} = require('./view');",'const {mount} = module.exports;')
(dest/'main.js').write_text(bundle,encoding='utf-8')
enabled=ROOT/'.obsidian/community-plugins.json'
plugins=json.loads(enabled.read_text(encoding='utf-8')) if enabled.exists() else []
if 'mock-trial-graph' not in plugins: plugins.append('mock-trial-graph')
enabled.write_text(json.dumps(plugins,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Installed: mock-trial-graph（読取専用・外部通信なし）')
