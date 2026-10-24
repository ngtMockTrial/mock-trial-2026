"""2026-10-21の再構築。本文・人の判断・証拠状態・ID・関係を維持して表示属性を追加。"""
import json
import re
from pathlib import Path
import yaml
def default_priority(ident, kind):
    if ident == 'T00': return 5
    if ident in {'T01','D09'}: return 4
    return 3 if kind in {'要証事実','推認','反論'} else 2

ROOT=Path(__file__).resolve().parents[1]
for path in (ROOT/'検討/ノート').glob('*.md'):
    text=path.read_text(encoding='utf-8')
    front,body=text.split('---',2)[1:]
    meta=yaml.safe_load(front)
    if 'display_priority' in meta: continue
    priority=default_priority(meta['id'],meta['kind'])
    extra='\n# 表示用。証拠力・有罪確率・人のレビューとは独立。\n'
    extra+=f'display_priority: {priority}\n'
    tags=list(meta.get('tags',[]))
    tags+=['論証/正本','立場/'+meta['side'],'種類/'+meta['kind']]
    extra+='tags: '+json.dumps(list(dict.fromkeys(tags)),ensure_ascii=False)+'\n'
    aliases=list(meta.get('aliases',[]))+[meta['id']+' '+meta['title']]
    extra+='aliases: '+json.dumps(list(dict.fromkeys(aliases)),ensure_ascii=False)+'\n'
    # 既存タグ・別名がある場合は重複キーを作らず停止する。
    if 'tags' in meta or 'aliases' in meta: raise ValueError('既存属性の手動統合が必要: '+str(path))
    body+='\n- 2026-10-21：構造の再構築に伴い立場・種類のタグ、別名、表示重要度を追加。出典・命題・支持反論関係・証拠状態・人のレビューは維持。重要度は表示の初期値。\n'
    path.write_text('---'+front.rstrip()+extra+'---'+body,encoding='utf-8')
print('表示構造を移行しました')
