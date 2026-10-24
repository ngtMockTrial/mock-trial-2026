const {Plugin, ItemView, Notice} = require('obsidian');
const {mount} = require('./view');
const TYPE = 'mock-trial-structure';
const DATA = '検討/構造グラフ.json';
class TrialView extends ItemView {
  getViewType(){return TYPE;}
  getDisplayText(){return '模擬裁判・構造グラフ';}
  getIcon(){return 'network';}
  async onOpen(){
    await this.refresh();
    this.registerEvent(this.app.vault.on('modify', file => {
      if(file.path===DATA) this.refresh();
      else if(file.path.startsWith('検討/ノート/') && this.graph) this.graph.stale();
    }));
  }
  async refresh(){
    try {
      const data=JSON.parse(await this.app.vault.adapter.read(DATA));
      // 起動前に編集された正本についても生成時のハッシュで未更新を検知。
      const crypto=require('crypto');
      let stale=false;
      for(const [path,hash] of Object.entries(data.source_hashes)){
        const bytes=await this.app.vault.adapter.readBinary(path);
        if(crypto.createHash('sha256').update(Buffer.from(bytes)).digest('hex')!==hash) stale=true;
      }
      this.graph?.destroy();
      this.graph=mount(this.contentEl,data,path=>this.app.workspace.openLinkText(path,'',true));
      if(stale) this.graph.stale();
    } catch(e) {
      this.contentEl.empty();
      this.contentEl.createEl('p',{text:'グラフを読み込めません。検討を更新.cmdを実行してください。 '+e.message});
    }
  }
  async onClose(){this.graph?.destroy();}
}
module.exports=class TrialPlugin extends Plugin {
  async onload(){
    this.registerView(TYPE,leaf=>new TrialView(leaf));
    const open=async()=>{
      let leaf=this.app.workspace.getLeavesOfType(TYPE)[0];
      if(!leaf){leaf=this.app.workspace.getLeaf('tab');await leaf.setViewState({type:TYPE,active:true});}
      this.app.workspace.revealLeaf(leaf);
    };
    this.addRibbonIcon('network','模擬裁判・構造グラフを開く',open);
    this.addCommand({id:'open',name:'構造グラフを開く',callback:open});
    this.addCommand({id:'refresh',name:'構造グラフを再読込',callback:()=>{
      this.app.workspace.getLeavesOfType(TYPE).forEach(l=>l.view.refresh());
      new Notice('生成データを再読込しました。正本変更の反映は検討を更新.cmdで行います。');
    }});
    this.registerObsidianProtocolHandler('trial-graph',open);
  }
};
