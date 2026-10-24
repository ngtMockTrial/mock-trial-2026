/* Browser-compatible view. All note text is inserted with textContent, never HTML. */
(function(root){
  const NS='http://www.w3.org/2000/svg';
  const COLORS={'検察':'#3978b7','弁護':'#be5364','共通':'#71818b'};
  const ROWS=[['最終目標',['最終結論']],['要証事実',['要証事実']],['推認・反論',['推認','反論']],['事実命題',['間接事実']],['証拠',['証拠']],['確認課題',['確認課題']],['準備専用・未獲得',['準備資料','供述獲得候補']]];
  const RELS={inputs:'支持',challenges:'反論',checks:'確認',preparation:'準備のみ',potential_supports:'将来候補'};
  function el(tag,attrs={},text){const e=document.createElement(tag);Object.entries(attrs).forEach(([k,v])=>k==='class'?e.className=v:e.setAttribute(k,v));if(text!==undefined)e.textContent=text;return e;}
  function svg(tag,attrs={},text){const e=document.createElementNS(NS,tag);Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,v));if(text!==undefined)e.textContent=text;return e;}
  function layout(nodes){
    const positions={},rows=[];let y=72;
    ROWS.forEach(([label,kinds])=>{
      const members=nodes.filter(n=>kinds.includes(n.kind));
      const max=Math.max(1,...['検察','共通','弁護'].map(side=>members.filter(n=>n.side===side).length));
      const height=label==='最終目標'?210:Math.ceil(max/2)*174+50;
      rows.push({label,y,height});
      ['検察','共通','弁護'].forEach((side,lane)=>{
        members.filter(n=>n.side===side).sort((a,b)=>b.priority-a.priority||a.id.localeCompare(b.id)).forEach((n,i)=>{
          positions[n.id]={x:label==='最終目標'?285:190+lane*440+(i%2)*200,y:y+85+Math.floor(i/2)*174};
        });
      }); y+=height;
    });return {positions,rows,height:y+20};
  }
  function mount(host,data,open){
    host.replaceChildren();host.classList.add('trial-graph');
    const COLORS=host.closest('.theme-dark')?{'検察':'#77b9fb','弁護':'#f18c9a','共通':'#a4b3bf'}:{'検察':'#286398','弁護':'#a93850','共通':'#536572'};
    let selected=null,zoom=.8,query='',side='すべて',kind='すべて',relation='すべて',neighborhood=false;
    const byid=Object.fromEntries(data.nodes.map(n=>[n.id,n]));
    const top=el('header',{class:'tg-heading'});host.append(top);
    top.append(el('h2',{},'模擬裁判の論証構造'),el('p',{},'大きさ＝表示上の重要度 ／ 色＝立場 ／ 形＝種類。事実命題も認定済みとは限りません。'));
    const stale=el('p',{class:'tg-stale',hidden:''},'正本に変更があります。「検討を更新.cmd」を実行してください。この図は更新前の内容です。');host.append(stale);
    const toolbar=el('div',{class:'tg-toolbar'});host.append(toolbar);
    function select(label,values,change){const wrap=el('label',{},label+' '),s=el('select',{'aria-label':label});values.forEach(v=>s.append(el('option',{value:v},v)));s.addEventListener('change',()=>{change(s.value);render();});wrap.append(s);toolbar.append(wrap);return s;}
    const search=el('input',{type:'search',name:'trial-search',autocomplete:'off',placeholder:'ID・主張・情報源を検索…','aria-label':'ノートを検索'});toolbar.append(search);search.addEventListener('input',()=>{query=search.value.toLowerCase();render();});
    select('立場',['すべて','検察','弁護','共通'],v=>side=v);
    select('種類',['すべて',...new Set(data.nodes.map(n=>n.kind))],v=>kind=v);
    select('線',['すべて',...Object.values(RELS)],v=>relation=v);
    const near=el('label'),check=el('input',{type:'checkbox'});near.append(check,document.createTextNode(' 選択点の周辺のみ'));toolbar.append(near);check.addEventListener('change',()=>{neighborhood=check.checked;render();});
    const zoomLabel=el('label',{},'拡大 '),range=el('input',{type:'range',min:'.4',max:'1.6',step:'.1',value:'.8','aria-label':'グラフの拡大率'});zoomLabel.append(range);toolbar.append(zoomLabel);range.addEventListener('input',()=>{zoom=Number(range.value);size();});
    const reset=el('button',{type:'button'},'選択解除');toolbar.append(reset);reset.onclick=()=>{selected=null;render();detail();};
    host.append(el('p',{class:'tg-legend'},'青＝検察　灰＝共通　赤＝弁護 ｜ ◎目標　六角形＝要証事実　◇推認　△反論　○事実命題　□証拠　?確認　破線枠＝準備・供述候補 ｜ 緑の小札＝採用資料、黄の小札＝留保・未獲得・条件付き'));
    const count=el('div',{class:'tg-count','aria-live':'polite'});host.append(count);
    const body=el('div',{class:'tg-body'}),viewport=el('div',{class:'tg-viewport',tabindex:'0','aria-label':'構造グラフ。スクロールで移動。点を選択すると接続を表示。'}),panel=el('aside',{class:'tg-detail','aria-label':'選択したノートの詳細'});host.append(body);body.append(viewport,panel);
    const canvas=svg('svg',{role:'group','aria-label':'立場と種類で区切った論証グラフ'});viewport.append(canvas);
    const fit=el('button',{type:'button'},'全幅に合わせる');toolbar.append(fit);
    fit.onclick=()=>{zoom=Math.max(.4,Math.min(1.6,(viewport.clientWidth-16)/1370));range.value=String(zoom);size();};
    let currentHeight=1000;
    function size(){canvas.setAttribute('width',1370*zoom);canvas.setAttribute('height',currentHeight*zoom);}
    function choose(id){selected=id;render();detail();}
    function detail(){
      panel.replaceChildren();
      if(!selected){panel.append(el('h3',{},'点を選ぶと根拠を読めます'),el('p',{},'関係する線だけを強調します。正本を開いて、出典・前提・反論・人のレビューを編集できます。'),el('p',{},'T00は検察側の最終立証目標です。弁護側には無実の証明や真犯人の特定を要求しません。'));return;}
      const n=byid[selected];panel.append(el('h3',{},n.id+' '+n.title),el('p',{class:'tg-meta'},n.side+' ／ '+n.kind+' ／ 重要度 '+n.priority),el('p',{},'資料・命題の状態：'+n.status),el('p',{},'利用状態：'+n.availability),el('p',{},'人のレビュー：'+n.review),el('p',{},n.summary));
      const button=el('button',{type:'button'},'正本・出典・レビューを開く');button.onclick=()=>open(n.path);panel.append(button);
      const edges=data.edges.filter(e=>e.source===selected||e.target===selected);
      for(const incoming of [true,false]){
        const part=edges.filter(e=>incoming?e.target===selected:e.source===selected);
        panel.append(el('h4',{},incoming?'この点へ向かう関係':'この点から向かう関係'));
        if(!part.length)panel.append(el('p',{},'なし'));
        part.forEach(e=>{const id=incoming?e.source:e.target,b=el('button',{type:'button',class:'tg-connection'},e.label+'：'+id+' '+byid[id].title);b.onclick=()=>choose(id);panel.append(b);});
      }
      panel.append(el('p',{class:'tg-meta'},'準備・将来候補の線は現在の支持に数えません。関係の編集は正本の属性で行います。'));
    }
    function render(){
      let nodes=data.nodes.filter(n=>(side==='すべて'||n.side===side)&&(kind==='すべて'||n.kind===kind)&&(!query||[n.id,n.title,...n.sources].join(' ').toLowerCase().includes(query)));
      if(neighborhood&&selected){const ids=new Set([selected]);data.edges.filter(e=>e.source===selected||e.target===selected).forEach(e=>{ids.add(e.source);ids.add(e.target);});nodes=nodes.filter(n=>ids.has(n.id));}
      const visible=new Set(nodes.map(n=>n.id));
      const edges=data.edges.filter(e=>visible.has(e.source)&&visible.has(e.target)&&(relation==='すべて'||RELS[e.field]===relation));
      const grid=layout(nodes);currentHeight=grid.height;canvas.setAttribute('viewBox','0 0 1370 '+currentHeight);canvas.replaceChildren();size();
      count.textContent=nodes.length+' / '+data.nodes.length+'命題・資料、'+edges.length+'関係を表示。上下へスクロールできます。';
      const defs=svg('defs');canvas.append(defs);
      ['#84929d','#be5364','#a77c14'].forEach((color,i)=>{const marker=svg('marker',{id:'tg-arrow-'+i,viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:7,markerHeight:7,orient:'auto-start-reverse'});marker.append(svg('path',{d:'M0 0 L10 5 L0 10 Z',fill:color}));defs.append(marker);});
      ['検察','共通','弁護'].forEach((s,i)=>{canvas.append(svg('rect',{x:90+i*440,y:0,width:430,height:currentHeight,fill:COLORS[s],'fill-opacity':.045}));canvas.append(svg('text',{x:305+i*440,y:35,'text-anchor':'middle',fill:COLORS[s],'font-size':24,'font-weight':700},s==='共通'?'双方共通の資料・事実命題':s+'側'));});
      grid.rows.forEach(r=>{canvas.append(svg('line',{x1:90,y1:r.y,x2:1370,y2:r.y,stroke:'#89959e','stroke-opacity':.3}));const label=svg('text',{x:14,y:r.y+28,'font-size':15,fill:'currentColor'});Array.from(r.label).forEach((c,i)=>label.append(svg('tspan',{x:24,dy:i?20:0},c)));canvas.append(label);});
      edges.forEach(e=>{
        const a=grid.positions[e.source],b=grid.positions[e.target],na=byid[e.source],nb=byid[e.target];
        const dx=b.x-a.x,dy=b.y-a.y,length=Math.hypot(dx,dy)||1;
        const x1=a.x+dx/length*(na.radius+7),y1=a.y+dy/length*(na.radius+7),x2=b.x-dx/length*(nb.radius+9),y2=b.y-dy/length*(nb.radius+9);
        const active=selected&&(e.source===selected||e.target===selected),warning=e.conditional||['preparation','potential_supports','checks'].includes(e.field);
        const index=e.field==='challenges'?1:warning?2:0,color=['#84929d','#be5364','#a77c14'][index];
        const path=svg('path',{d:`M ${x1} ${y1} Q ${(x1+x2)/2+40} ${(y1+y2)/2} ${x2} ${y2}`,fill:'none',stroke:color,'stroke-width':active?3:1.5,'stroke-opacity':selected?(active?.9:.08):.24,'stroke-dasharray':warning?'7 5':'none','marker-end':`url(#tg-arrow-${index})`,'data-field':e.field});
        path.append(svg('title',{},e.source+' → '+e.target+'：'+e.label));canvas.append(path);
        if(active)canvas.append(svg('text',{x:(x1+x2)/2+24,y:(y1+y2)/2-7,fill:color,'font-size':15,class:'tg-edge-label'},e.label));
      });
      nodes.forEach(n=>{
        const p=grid.positions[n.id],r=n.radius,c=COLORS[n.side],g=svg('g',{transform:`translate(${p.x} ${p.y})`,tabindex:0,role:'button','aria-label':n.id+' '+n.title+'、'+n.side+'、'+n.kind,'data-id':n.id,'data-radius':r,class:'tg-node'});
        const pending=['pending','candidate','conditional'].includes(n.state);
        let shape;const attrs={fill:c,'fill-opacity':selected===n.id?.28:.12,stroke:c,'stroke-width':selected===n.id?4:2};
        if(['証拠','準備資料','供述獲得候補'].includes(n.kind)){shape=svg('rect',{x:-r,y:-r,width:r*2,height:r*2,rx:n.kind==='証拠'?3:10,...attrs});if(n.kind!=='証拠')shape.setAttribute('stroke-dasharray','5 4');}
        else if(n.kind==='推認')shape=svg('polygon',{points:`0,${-r} ${r},0 0,${r} ${-r},0`,...attrs});
        else if(n.kind==='反論')shape=svg('polygon',{points:`0,${-r} ${r},${r*.8} ${-r},${r*.8}`,...attrs});
        else if(n.kind==='要証事実')shape=svg('polygon',{points:`${-r},0 ${-r/2},${-r*.86} ${r/2},${-r*.86} ${r},0 ${r/2},${r*.86} ${-r/2},${r*.86}`,...attrs});
        else shape=svg('circle',{r,...attrs});
        g.append(shape);if(n.id==='T00')g.append(svg('circle',{r:r-7,fill:'none',stroke:c,'stroke-width':2}));
        g.append(svg('text',{'text-anchor':'middle',dy:6,fill:c,'font-size':n.priority>=4?21:16,'font-weight':700},n.kind==='確認課題'?'? '+n.id:n.id));
        const title=n.title.match(/.{1,12}/gu)||[];title.forEach((t,i)=>g.append(svg('text',{'text-anchor':'middle',y:r+24+i*18,fill:'currentColor','font-size':15,'font-weight':n.priority>=4?700:400},t)));
        const badge=n.state==='available'?'採用資料':pending?(n.state==='candidate'?'未獲得':n.state==='pending'?'採否留保':'条件付き'):n.kind;
        g.append(svg('text',{'text-anchor':'middle',y:-r-12,fill:pending?'#8b670d':n.state==='available'?'#287146':c,'font-size':13,'font-weight':600},badge));
        g.append(svg('title',{},n.title+'\n'+n.kind+'・'+n.side+'\n'+n.availability));
        g.addEventListener('click',()=>choose(n.id));g.addEventListener('dblclick',()=>open(n.path));g.addEventListener('keydown',ev=>{if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();choose(n.id);}});canvas.append(g);
      });
    }
    render();detail();fit.click();
    return {stale:()=>stale.removeAttribute('hidden'),destroy:()=>host.replaceChildren()};
  }
  const api={mount,layout};if(typeof module!=='undefined')module.exports=api;else root.TrialGraph=api;
})(globalThis);
