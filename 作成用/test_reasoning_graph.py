"""検査が見逃してはいけないケースと、人の編集保護を検証する。"""
import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import obsidian_graph as native
import setup_extended_graph as extended

SPEC=importlib.util.spec_from_file_location('reasoning_graph',Path(__file__).with_name('reasoning_graph.py'))
graph=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(graph)


class ReasoningGraphTests(unittest.TestCase):
    def test_native_graph_sizes_follow_display_priority_without_altering_reviews(self):
        notes=graph.load_notes(graph.ROOT)
        before={i:(n['meta']['review'],n['meta']['status']) for i,n in notes.items()}
        files,_=native.native_graph_files(graph.ROOT,notes,graph.refs,graph.availability)
        metas=[graph.yaml.safe_load(c.split('---',2)[1]) for c in files.values()]
        nodes={m['graph_id']:m for m in metas if 'graph_id' in m}
        self.assertGreater(nodes['T00']['node_size'],max(m['node_size'] for i,m in nodes.items() if i!='T00'))
        self.assertGreater(nodes['T01']['node_size'],nodes['T02']['node_size'])
        self.assertEqual(nodes['E07']['kind'],'準備資料')
        self.assertIn('⚠',nodes['E07']['graph_label'])
        self.assertEqual(before,{i:(n['meta']['review'],n['meta']['status']) for i,n in notes.items()})

    def test_organic_refresh_never_adds_or_overwrites_pin_coordinates(self):
        dest=self.root/'.obsidian/plugins/extended-graph/data.json'
        dest.parent.mkdir(parents=True)
        data={'mockTrialLayout':'organic','states':[{'id':extended.STATE_ID,'pinNodes':{'人のノート.md':{'x':20,'y':30}}}]}
        dest.write_text(json.dumps(data),encoding='utf-8')
        before=dest.read_bytes()
        extended.sync_pins(self.root,{},None,None)
        self.assertEqual(dest.read_bytes(),before)

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/'検討'/'ノート').mkdir(parents=True)

    def note(self,ident,kind='推認',inputs=(),challenges=(),status='推論案',review='未レビュー',**extra):
        m=dict(id=ident,title='検証用の命題',kind=kind,side='共通',review=review,status=status,source_group=['同じ記録'],inputs=[f'[[検討/ノート/{x}]]' for x in inputs],challenges=[f'[[検討/ノート/{x}]]' for x in challenges],checks=[],answered_objections=[])
        m.update(extra)
        p=self.root/'検討'/'ノート'/f'{ident}.md'
        p.write_text('---\n'+'\n'.join(k+': '+json.dumps(v,ensure_ascii=False) for k,v in m.items())+'\n---\n\n## 図の要点\n検証する命題\n\n## 人間のコメント\n人が書いた重要なコメント\n\n## 反論への応答\n未記入。\n',encoding='utf-8')
        return p

    def approve(self,notes):
        for n in notes.values():
            n['meta'].update(review='採用',reviewer='検証者',reviewed_on='2026-10-20')

    def test_support_cycle_is_rejected(self):
        self.note('R01',inputs=['R02']);self.note('R02',inputs=['R01'])
        with self.assertRaisesRegex(ValueError,'循環'):
            graph.load_notes(self.root)

    def test_pending_premise_propagates_to_final_and_has_distinct_badges(self):
        notes=graph.load_notes(graph.ROOT)
        self.assertEqual(graph.availability(notes,'E02')[0],'available')
        self.assertEqual(graph.availability(notes,'E07')[0],'pending')
        self.assertEqual(graph.availability(notes,'W01')[0],'candidate')
        self.assertEqual(graph.availability(notes,'T00')[0],'conditional')
        data=graph.canvas_data(notes,list(notes));byid={n['id']:n for n in data['nodes']}
        self.assertNotEqual(byid['R01']['color'],byid['D01']['color'])
        self.assertNotEqual(byid['badge-E02']['color'],byid['badge-E07']['color'])
        self.assertTrue(any(e['fromNode']=='E07' and e['toNode']=='F03' and e['color']=='3' for e in data['edges']))

    def test_potential_testimony_does_not_count_as_existing_support(self):
        notes=graph.load_notes(graph.ROOT)
        self.assertNotIn('W01',graph.closure(notes,'T00'))
        self.assertNotIn('W02',graph.closure(notes,'T00'))
        self.note('W01',kind='供述獲得候補',status='未獲得')
        self.note('T01',kind='要証事実',inputs=['W01'])
        small=graph.load_notes(self.root);self.approve(small)
        self.assertTrue(any('現在の証拠として' in r for r in graph.gate(small,'T01')))

    def test_final_conclusion_is_unique_highest_claim_and_keeps_all_three_branches(self):
        notes=graph.load_notes(graph.ROOT)
        self.assertEqual(graph.refs(notes['T00'],'inputs'),['T01','T02','T03'])
        self.assertEqual(notes['T00']['meta']['title'],'被告人は有罪である')
        loc=graph.positions(notes,list(notes))
        self.assertTrue(all(loc['T00'][1]<pos[1] for ident,pos in loc.items() if ident!='T00'))
        self.assertEqual(len({loc[n][1] for n in ['T01','T02','T03']}),1)
        data=graph.canvas_data(notes,list(notes))
        for ident in ['T01','T02','T03']:
            self.assertTrue(any(e['fromNode']==ident and e['toNode']=='T00' for e in data['edges']))

    def test_missing_reference_is_rejected(self):
        self.note('R01',inputs=['E99'])
        with self.assertRaisesRegex(ValueError,'存在しない'):
            graph.load_notes(self.root)

    def test_human_approval_needs_attribution(self):
        self.note('R01',review='採用')
        with self.assertRaisesRegex(ValueError,'reviewer'):
            graph.load_notes(self.root)

    def test_held_evidence_blocks_transitive_target_even_after_human_approval(self):
        self.note('E01',kind='証拠',status='採否留保');self.note('R01',inputs=['E01']);self.note('T01',kind='要証事実',inputs=['R01'])
        notes=graph.load_notes(self.root);self.approve(notes)
        self.assertTrue(any('E01' in r and '採否留保' in r for r in graph.gate(notes,'T01')))

    def test_unanswered_objection_blocks_then_recorded_response_can_clear(self):
        self.note('E01',kind='証拠',status='採用済み');self.note('R01',inputs=['E01']);self.note('D01',kind='反論',challenges=['R01'])
        notes=graph.load_notes(self.root);self.approve(notes)
        self.assertTrue(any('D01' in r for r in graph.gate(notes,'R01')))
        notes['R01']['meta']['answered_objections']=['[[検討/ノート/D01]]']
        self.assertTrue(graph.gate(notes,'R01'))  # 空の応答欄では通らない
        notes['R01']['body']+='\n## 反論への応答\nD01に対する具体的な応答を人が記録した。\n'
        # 同名見出しを重ねる方法ではなく既存の欄を更新する
        notes['R01']['body']=notes['R01']['body'].replace('未記入。','D01に対する応答。残る限界も人が確認した。')
        self.assertEqual(graph.gate(notes,'R01'),[])

    def test_objection_links_do_not_create_false_support_cycle(self):
        self.note('R01');self.note('D01',kind='反論',inputs=['R01'],challenges=['R01'])
        self.assertEqual(len(graph.load_notes(self.root)),2)

    def test_layout_and_manual_cards_survive_refresh(self):
        path=self.root/'test.canvas'
        old={'nodes':[{'id':'E01','type':'file','file':'old.md','x':999,'y':-500,'width':450,'height':320},{'id':'hand','type':'text','text':'人の付箋','x':5,'y':5,'width':100,'height':100}], 'edges':[{'id':'manual-line','fromNode':'hand','toNode':'E01','label':'人の仮の線'}]}
        path.write_text(json.dumps(old),encoding='utf-8')
        new={'nodes':[dict(id='E01',type='file',file='new.md',x=0,y=0,width=420,height=300)],'edges':[]}
        result=graph.preserve_layout(new,path)
        self.assertEqual(result['nodes'][0]['x'],999)
        self.assertEqual(result['nodes'][0]['file'],'new.md')
        self.assertEqual(result['nodes'][1]['text'],'人の付箋')
        self.assertEqual(result['edges'][0]['label'],'人の仮の線')

    def test_approval_without_any_evidence_path_does_not_pass(self):
        self.note('T01',kind='要証事実')
        notes=graph.load_notes(self.root);self.approve(notes)
        self.assertTrue(any('支持経路がない' in r for r in graph.gate(notes,'T01')))

    def test_generated_edge_semantics_follow_notes_not_stale_canvas(self):
        path=self.root/'test.canvas'
        old={'nodes':[],'edges':[{'id':'inputs-E01-R01','fromNode':'D01','toNode':'T01','label':'古い矢印の意味','color':'6'}]}
        path.write_text(json.dumps(old),encoding='utf-8')
        fresh={'nodes':[],'edges':[{'id':'inputs-E01-R01','fromNode':'E01','toNode':'R01','label':'支える・前提','color':'4'}]}
        result=graph.preserve_layout(fresh,path)
        self.assertEqual(result['edges'][0]['fromNode'],'E01')
        self.assertEqual(result['edges'][0]['toNode'],'R01')
        self.assertEqual(result['edges'][0]['label'],'支える・前提')

    def test_court_confirmation_requires_an_existing_record(self):
        self.note('E01',kind='証拠',status='法廷確認済み',court_record='存在しない記録.md')
        self.note('T01',kind='要証事実',inputs=['E01'])
        notes=graph.load_notes(self.root);self.approve(notes)
        with patch.object(graph,'ROOT',self.root):
            self.assertTrue(any('記録ファイルがない' in r for r in graph.gate(notes,'T01')))

    def test_build_never_overwrites_human_notes_and_is_repeatable(self):
        p=self.note('E01',kind='証拠',status='採用済み')
        self.note('T01',kind='要証事実',inputs=['E01']);self.note('T02',kind='要証事実',inputs=['E01']);self.note('T03',kind='要証事実',inputs=['E01'])
        before=p.read_bytes();notes=graph.load_notes(self.root)
        with patch.object(graph,'ROOT',self.root),patch.object(graph,'VIEWS',{'test':['E01','T01']}):
            graph.build(notes)
            first=(self.root/'検討'/'Canvas'/'test.canvas').read_bytes()
            viewer=(self.root/'検討'/'つながりをたどる.html').read_bytes()
            graph.build(notes)
            self.assertEqual(first,(self.root/'検討'/'Canvas'/'test.canvas').read_bytes())
            self.assertEqual(viewer,(self.root/'検討'/'つながりをたどる.html').read_bytes())
        self.assertEqual(p.read_bytes(),before)


    def test_connection_guide_shows_both_directions_without_promoting_candidates(self):
        self.note('E01',kind='準備資料',status='採否留保')
        self.note('R01',inputs=['E01'])
        self.note('D01',kind='反論',challenges=['R01'])
        self.note('Q01',kind='確認課題',checks=['[[検討/ノート/R01]]'])
        self.note('W01',kind='供述獲得候補',status='未獲得',
                  preparation=['[[検討/ノート/E01]]'],potential_supports=['[[検討/ノート/R01]]'])
        guide=graph.connection_guide(graph.load_notes(self.root))
        r_section=guide.split('## R01\n',1)[1].split('\n## W01',1)[0]
        for label in ['前提として読む','このカードに向けられた反論','このカードについて残る確認事項','将来支え得る供述候補（未獲得）']:
            self.assertIn(label,r_section)
        self.assertIn('現時点は根拠に不可・採否留保調書',guide)
        self.assertIn('供述獲得後の支持候補（現在は利用不可）',guide)
        self.assertIn('### このカードを前提に使う先',guide)
        self.assertEqual(guide.count('\n## R01\n'),1)


    def test_viewer_exports_exact_relations_and_escapes_script_content(self):
        notes=graph.load_notes(graph.ROOT)
        notes['R01']['body']+='\n</script><script>alert(1)</script>'
        output=graph.connection_view(notes)
        data=re.search(r'<script id="graph-data" type="application/json">(.*?)</script>',output,re.S)[1]
        payload=json.loads(data)['notes']
        self.assertEqual(set(payload),set(notes))
        self.assertNotIn('<script>',data)
        for ident,note in notes.items():
            self.assertEqual(payload[ident]['body'],note['body'])
            for field in ['inputs','challenges','checks','preparation','potential_supports']:
                self.assertEqual(payload[ident][field],graph.refs(note,field))
        self.assertEqual(payload['E07']['state'],'pending')
        self.assertEqual(payload['W01']['state'],'candidate')


    def test_native_graph_reproduces_canvas_relations_without_intermediate_nodes(self):
        notes=graph.load_notes(graph.ROOT)
        files,edges=native.native_graph_files(graph.ROOT,notes,graph.refs,graph.availability)
        canvas=graph.canvas_data(notes,list(notes))
        self.assertEqual({(e['fromNode'],e['toNode'],e['id'].split('-')[0]) for e in canvas['edges']},
                         {(e['source'],e['target'],e['field']) for e in edges})
        self.assertEqual(len(files),len(notes))
        paths={graph.yaml.safe_load(content.split('---',2)[1])['graph_id']:path[:-3] for path,content in files.items()}
        displayed=set()
        scopes={}
        for path,content in files.items():
            meta=graph.yaml.safe_load(content.split('---',2)[1])
            ident=meta['graph_id'];scopes[ident]=meta['graph_scope']
            # 正本への編集リンクを除く全wikilinkが、実際の向きの直接接続。
            for target in re.findall(r'\[\[([^]|]+)(?:\|[^]]+)?\]\]',content.replace('\\|','|')):
                if target in paths.values():
                    displayed.add((ident,next(key for key,value in paths.items() if value==target)))
        self.assertEqual(displayed,{(e['source'],e['target']) for e in edges})
        # Counts are a snapshot, not a limit: collaborators may add new claims.
        self.assertEqual(set(scopes),set(notes))
        expected_main={ident for ident,note in notes.items()
                       if note['meta']['kind'] not in {'確認課題','準備資料','供述獲得候補'}}
        self.assertEqual({ident for ident,scope in scopes.items() if scope=='本筋'},expected_main)
        self.assertTrue(all(scopes[key]=='準備・確認' for key in ['Q01','Q05','E07','E09','W01','W02']))
        for e in edges:
            content=files[paths[e['source']]+'.md']
            self.assertIn(f'| {e["label"]} | [[{paths[e["target"]]}\\|',content)
            target=files[paths[e['target']]+'.md']
            self.assertIn(f'| {e["label"]} | [{e["source"]} ',target)
        self.assertTrue(any(e['source']=='D01' and e['target']=='R01' and e['label']=='反論' for e in edges))
        self.assertTrue(any(e['source']=='E07' and e['target']=='F03' and e['label']=='条件付き支持' for e in edges))
        self.assertTrue(any(e['source']=='W01' and e['field']=='potential_supports' and e['label']=='将来候補' for e in edges))

    def test_obsolete_relation_files_are_removed_only_if_unedited(self):
        self.note('E01',kind='証拠',status='採用済み')
        notes=graph.load_notes(self.root)
        native.write_native_graph(self.root,notes,graph.refs,graph.availability)
        ledger=self.root/'作成用/構造化確認/グラフ生成台帳.json'
        previous=json.loads(ledger.read_text(encoding='utf-8'))
        relative=native.FOLDER+'/接続/支持 E01 → T01.md'
        old=self.root/relative;old.parent.mkdir(parents=True)
        old.write_text('old generated relation\n',encoding='utf-8')
        previous[relative]=native.digest(old.read_text(encoding='utf-8'))
        ledger.write_text(json.dumps(previous),encoding='utf-8')
        old.write_text('人の追記',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'生成外の編集'):
            native.write_native_graph(self.root,notes,graph.refs,graph.availability)
        self.assertEqual(old.read_text(encoding='utf-8'),'人の追記')
        old.write_text('old generated relation\n',encoding='utf-8')
        native.write_native_graph(self.root,notes,graph.refs,graph.availability)
        self.assertFalse(old.exists())
        native.check_native_graph(self.root,notes,graph.refs,graph.availability)

    def test_native_graph_preserves_manual_derivative_edits_and_source_notes(self):
        p=self.note('E01',kind='証拠',status='採用済み')
        self.note('T01',kind='要証事実',inputs=['E01'])
        notes=graph.load_notes(self.root);before=p.read_bytes()
        files,_=native.write_native_graph(self.root,notes,graph.refs,graph.availability)
        native.check_native_graph(self.root,notes,graph.refs,graph.availability)
        target=self.root/next(iter(files))
        target.write_text(target.read_text(encoding='utf-8')+'人の追記\n',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'生成外の編集'):
            native.write_native_graph(self.root,notes,graph.refs,graph.availability)
        self.assertTrue(target.read_text(encoding='utf-8').endswith('人の追記\n'))
        self.assertEqual(p.read_bytes(),before)

    def test_native_graph_configuration_preserves_unrelated_bookmarks_and_regular_build_keeps_preferences(self):
        self.note('E01',kind='証拠',status='採用済み')
        notes=graph.load_notes(self.root)
        config=self.root/'.obsidian';config.mkdir()
        bookmark=dict(type='file',path='人間のノート.md',title='人のブックマーク')
        (config/'bookmarks.json').write_text(json.dumps(dict(items=[bookmark])),encoding='utf-8')
        native.configure_graph(self.root,notes,graph.refs,graph.availability)
        native.configure_graph(self.root,notes,graph.refs,graph.availability)
        saved=json.loads((config/'bookmarks.json').read_text(encoding='utf-8'))
        self.assertEqual(saved['items'][0],bookmark)
        self.assertEqual(len(saved['items']),2)
        self.assertEqual(len(saved['items'][1]['items']),2)
        options=json.loads((config/'graph.json').read_text(encoding='utf-8'))
        self.assertTrue(options['showArrow'])
        self.assertEqual(len(options['colorGroups']),4)
        self.assertEqual(options['colorGroups'][0]['query'],'[graph_id:T00]')
        self.assertEqual(options['search'],native.MAIN_QUERY)
        (config/'graph.json').write_text('{"search":"人が調整した検索"}',encoding='utf-8')
        native.write_native_graph(self.root,notes,graph.refs,graph.availability)
        self.assertEqual(json.loads((config/'graph.json').read_text(encoding='utf-8'))['search'],'人が調整した検索')


if __name__=='__main__':
    unittest.main(verbosity=2)
