(() => {
  'use strict';
  const data = window.TRIAL_GRAPH;
  const $ = id => document.getElementById(id);
  if (!data?.notes) {
    $('detail-content').textContent = 'データを読み込めませんでした。ページを再読込してください。';
    return;
  }
  const notes = data.notes;
  const colors = {検察:'#3978b7', 弁護:'#be5364', 共通:'#71818b'};
  const bright = {検察:'#76b4ef', 弁護:'#ef94a4', 共通:'#adbecb'};
  const names = {inputs:'支持・前提', challenges:'反論', checks:'確認', preparation:'準備のみ', potential_supports:'将来候補'};
  const warningStates = new Set(['pending','candidate','conditional']);
  const query = new URLSearchParams(location.search);
  const sharedSettings = data.graph_settings.options;
  const settingsKey = 'mock-trial-graph-' + data.graph_settings.settings_hash;
  let settings = {...sharedSettings};
  try {
    const saved = JSON.parse(localStorage.getItem(settingsKey));
    if (saved) for (const key of Object.keys(sharedSettings)) {
      if (typeof saved[key] === typeof sharedSettings[key] &&
          (typeof saved[key] !== 'number' || Number.isFinite(saved[key]))) settings[key] = saved[key];
    }
  } catch (_) { /* Storage is optional, including file: previews. */ }
  let scope = query.get('scope') === 'detail' ? 'detail' : 'main';
  let selected = 'T01', search = query.get('q') || '', side = query.get('side') || '';
  let nodeElements = [], edgeElements = [], visible = [], edges = [], positions = {};
  let width = 600, height = 800, zoom = 1, panX = 0, panY = 0;
  let dragging = null, moved = false;
  let simulation = null, simulationNodes = [], hovered = null, emphasized = null, userPaused = false;
  let fitScale = 1, worldCenter = {x:0,y:0}, plotCenterY=400, automaticFit = true, startedAt = 0;
  const pointCache = new Map();
  const reduceMotion = matchMedia('(prefers-reduced-motion:reduce)');
  const ns = 'http://www.w3.org/2000/svg';
  const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const sourceURL = path => data.repository + '/blob/main/' + path.split('/').map(encodeURIComponent).join('/');
  $('repository').href = data.repository;
  $('search').value = search;
  $('side').value = side;
  for (const [sideName,selector] of Object.entries({検察:'.dot.prosecution',弁護:'.dot.defense',共通:'.dot.common'})) {
    const group=settings.colorGroups.find(g=>g.query===`[side:${sideName}]`);
    if(group)document.querySelector(selector).style.background='#'+group.color.rgb.toString(16).padStart(6,'0');
  }

  function updateURL() {
    const params = new URLSearchParams();
    if (scope === 'detail') params.set('scope', scope);
    if (search) params.set('q', search);
    if (side) params.set('side', side);
    history.replaceState(null, '', location.pathname + (params.size ? '?' + params : '') + location.hash);
  }

  function listedNotes() {
    const term = search.toLocaleLowerCase();
    return Object.values(notes).filter(note =>
      (scope === 'detail' || note.scope === 'main') && (!side || note.side === side) &&
      (!term || (note.id + note.title + note.kind + note.html.replace(/<[^>]*>/g, '')).toLocaleLowerCase().includes(term))
    ).sort((a,b) => b.priority - a.priority || a.id.localeCompare(b.id));
  }

  function renderIndex() {
    visible = listedNotes();
    $('main-scope').setAttribute('aria-pressed', scope === 'main');
    $('detail-scope').setAttribute('aria-pressed', scope === 'detail');
    $('count').textContent = visible.length + '件';
    $('empty').hidden = visible.length !== 0;
    $('note-list').innerHTML = visible.map(note => `<a class="note-link" href="#${note.id}" data-note="${note.id}" aria-current="${selected === note.id}" style="--node-color:${colors[note.side]}"><span class="note-id">${note.id}${warningStates.has(note.state) ? ' ⚠' : ''}</span><span>${esc(note.title)}<small>${esc(note.side)} · ${esc(note.kind)}</small></span></a>`).join('');
    $('graph-title').textContent = scope === 'main' ? '論証の本筋' : '準備・確認を含む全体';
    updateURL();
    renderGraph();
  }

  function relationSection(title, ids, field) {
    if (!ids.length) return '';
    return `<h3>${title}</h3>` + ids.map(id => `<a class="relation-link" href="#${id}"><span style="color:${colors[notes[id].side]}">${id}</span><span>${esc(notes[id].title)}</span><small>${names[field]}</small></a>`).join('');
  }

  function renderNote(id) {
    const note = notes[id];
    if (!note) return;
    selected = id;
    let needsIndex = false;
    if (note.scope === 'detail' && scope !== 'detail') {scope = 'detail'; needsIndex = true;}
    if (side && note.side !== side) {side = ''; $('side').value = ''; needsIndex = true;}
    if (search && !listedNotes().some(n => n.id === id)) {search = ''; $('search').value = ''; needsIndex = true;}
    if (needsIndex) renderIndex();
    $('detail').classList.remove('doc-mode');
    const relationHTML = relationSection('前提として読む', note.inputs, 'inputs') +
      relationSection('この命題を前提に使う先', Object.values(notes).filter(n => n.inputs.includes(id)).map(n => n.id), 'inputs') +
      relationSection('この命題に向けられた反論', Object.values(notes).filter(n => n.challenges.includes(id)).map(n => n.id), 'challenges') +
      relationSection('この命題が反論する先', note.challenges, 'challenges') +
      relationSection('残る確認事項', Object.values(notes).filter(n => n.checks.includes(id)).map(n => n.id), 'checks') +
      relationSection('確認する対象', note.checks, 'checks') +
      relationSection('供述獲得の準備資料', note.preparation, 'preparation') +
      relationSection('将来支え得る候補・現在は根拠に不可', Object.values(notes).filter(n => n.potential_supports.includes(id)).map(n => n.id), 'potential_supports') +
      relationSection('将来の支持対象・現在は利用不可', note.potential_supports, 'potential_supports');
    $('detail-meta').innerHTML = `<div class="detail-topline"><span style="color:${colors[note.side]}">${note.id} ／ ${esc(note.side)}</span><a href="${sourceURL(note.path)}">正本をGitHubで開く ↗</a></div><h2 class="note-title">${esc(note.title)}</h2><div class="note-category">${esc(note.kind)} · 人の判断：${esc(note.review)}</div><div class="state-note ${note.state === 'available' ? 'available' : ''}"><p>${esc(note.availability)}</p><p>資料・命題の状態：${esc(note.status)}</p></div>`;
    $('detail-content').innerHTML = `<div class="relation-section">${relationHTML || '<p>接続は未設定です。</p>'}</div><h3 class="body-heading">本文・出典・検討の記録</h3><article class="markdown">${note.html}</article><p class="revision">公開データ：${data.content_hash.slice(0,12)} ／ 正本の変更はmainへのマージ後に反映</p>`;
    $('detail').scrollTop = 0;
    document.title = `${id} ${note.title}｜模擬裁判`;
    for (const a of document.querySelectorAll('.note-link')) a.setAttribute('aria-current', a.dataset.note === id);
    highlightGraph();
  }

  function renderDocument(path, heading) {
    const doc = data.documents[path];
    if (!doc) {
      $('detail-content').innerHTML = '<h2>資料が見つかりません</h2><p><a href="#doc=docs%2FREADME.md">資料一覧へ戻る</a></p>';
      return;
    }
    $('detail').classList.add('doc-mode');
    $('detail-meta').innerHTML = `<div class="detail-topline"><span>資料と使い方</span><a href="${sourceURL(path)}">GitHubで開く ↗</a></div><label class="filter-label" for="document-picker">資料を選ぶ</label><select id="document-picker" class="doc-picker">${Object.values(data.documents).filter(d => !d.path.includes('/原文/')).map(d => `<option value="${esc(d.path)}" ${d.path === path ? 'selected' : ''}>${esc(d.title)}</option>`).join('')}</select>`;
    $('document-picker').addEventListener('change', e => {location.hash = 'doc=' + encodeURIComponent(e.target.value);});
    $('detail-content').innerHTML = `<article class="markdown">${doc.html}</article>`;
    document.title = `${doc.title}｜模擬裁判`;
    $('detail').scrollTop = 0;
    if (heading) scrollHeading(heading);
  }

  function scrollHeading(heading) {
    const target = [...$('detail-content').querySelectorAll('[id]')].find(el => el.id === heading || el.textContent === heading);
    if (target) target.scrollIntoView({block:'start'});
  }

  function route() {
    const hash = location.hash.slice(1);
    if (hash.startsWith('doc=')) {
      const params = new URLSearchParams(hash);
      renderDocument(params.get('doc'), params.get('heading'));
    } else if (hash.startsWith('heading=')) {
      scrollHeading(decodeURIComponent(hash.slice(8)));
    } else {
      renderNote(notes[hash] ? hash : 'T01');
    }
  }

  function nodeRadius(id) {
    return ({1:5,2:7,3:10,4:14,5:22}[notes[id].priority] || 7) * settings.nodeSizeMultiplier;
  }

  function graphColor(note) {
    const group = settings.colorGroups.find(g=>g.query===`[graph_id:${note.id}]`) || settings.colorGroups.find(g=>g.query===`[side:${note.side}]`);
    return group ? '#' + group.color.rgb.toString(16).padStart(6,'0') : bright[note.side];
  }

  function fitWorld() {
    if (!simulationNodes.length) return;
    const minX=Math.min(...simulationNodes.map(p=>p.x)),maxX=Math.max(...simulationNodes.map(p=>p.x));
    const minY=Math.min(...simulationNodes.map(p=>p.y)),maxY=Math.max(...simulationNodes.map(p=>p.y));
    const top=width<560?115:145,bottom=width<560?120:145;
    plotCenterY=(top+height-bottom)/2;
    fitScale=Math.min((width-120)/Math.max(maxX-minX,200),(height-top-bottom)/Math.max(maxY-minY,200),1.5);
    worldCenter={x:(minX+maxX)/2,y:(minY+maxY)/2};
    zoom=1;panX=0;panY=0;
  }

  function setRunning(value) {
    $('graph').dataset.running=String(value);
    $('pause-layout').textContent=value?'配置を止める':'配置を動かす';
    $('pause-layout').setAttribute('aria-pressed',!value);
  }

  function stopSimulation() {if(simulation)simulation.stop();setRunning(false);}

  function restartSimulation(alpha=.35) {
    if (!simulation || userPaused || document.hidden) return;
    startedAt=performance.now();
    if(reduceMotion.matches){simulation.stop().alpha(alpha).alphaTarget(0).tick(160);if(automaticFit)fitWorld();paint();setRunning(false);}
    else{simulation.alpha(Math.max(alpha,simulation.alpha())).restart();setRunning(true);}
  }

  function applyForces() {
    if(!simulation)return;
    // These conversions preserve the meaning of the sliders, not Obsidian's private solver.
    simulation.force('x',d3.forceX(0).strength(settings.centerStrength*.1))
      .force('y',d3.forceY(0).strength(settings.centerStrength*.1))
      .force('charge',d3.forceManyBody().strength(-settings.repelStrength*60))
      .force('link',d3.forceLink(edges.map(e=>({...e}))).id(n=>n.id).distance(settings.linkDistance).strength(settings.linkStrength))
      .force('collide',d3.forceCollide(n=>nodeRadius(n.id)/Math.max(fitScale,.15)+16).strength(.7));
  }

  function svgElement(tag, attributes) {
    const element = document.createElementNS(ns, tag);
    for (const [key,value] of Object.entries(attributes)) element.setAttribute(key,value);
    return element;
  }

  function renderGraph() {
    stopSimulation();
    const rect = $('graph').getBoundingClientRect(); width=rect.width; height=rect.height;
    $('graph').setAttribute('viewBox',`0 0 ${width} ${height}`);
    let graphNotes=visible;
    if(!settings.showOrphans){const candidates=new Set(graphNotes.map(n=>n.id));const connected=new Set();for(const edge of data.edges)if(candidates.has(edge.source)&&candidates.has(edge.target)){connected.add(edge.source);connected.add(edge.target);}graphNotes=graphNotes.filter(n=>connected.has(n.id));}
    $('graph-title').textContent=scope==='main'?'論証の本筋':'準備・確認を含む全体';
    const ids=graphNotes.map(n=>n.id),set=new Set(ids);
    edges=data.edges.filter(e=>set.has(e.source)&&set.has(e.target));
    simulationNodes=ids.map((id,i)=>{
      if(!pointCache.has(id))pointCache.set(id,{id,x:Math.cos(i*2.39996)*Math.sqrt(i+1)*70,y:Math.sin(i*2.39996)*Math.sqrt(i+1)*70});
      return pointCache.get(id);
    });
    simulation=d3.forceSimulation(simulationNodes).stop().alphaDecay(.055).velocityDecay(.4);
    applyForces();
    simulation.tick(90);fitWorld();automaticFit=true;
    simulation.on('tick',()=>{paint();if(performance.now()-startedAt>3500&&!dragging)stopSimulation();});
    simulation.on('end',()=>{if(automaticFit)fitWorld();paint();setRunning(false);});
    $('graph').dataset.engine='d3-force';
    $('graph-count').textContent=`${ids.length}点・${edges.length}接続`;
    $('edges').replaceChildren();$('nodes').replaceChildren();
    edgeElements=edges.map(edge=>{
      const line=svgElement('line',{class:'edge','data-field':edge.field});
      const title=svgElement('title',{});title.textContent=`${edge.source} → ${edge.target}：${names[edge.field]}`;line.append(title);$('edges').append(line);
      return {edge,element:line};
    });
    nodeElements=graphNotes.map(note=>{
      const node=svgElement('a',{href:'#'+note.id,class:'graph-node'+(warningStates.has(note.state)?' warning':''),'data-node':note.id,'aria-label':`${note.id} ${note.title}、${note.side}、${note.kind}`,tabindex:0});
      const radius=nodeRadius(note.id);
      const circle=svgElement('circle',{r:radius,fill:graphColor(note)});
      const alignRight=pointCache.get(note.id).x>worldCenter.x+width*.18/fitScale;
      const labelX=alignRight ? -radius-5 : radius+5;
      const anchor=alignRight?'end':'start';
      const label=svgElement('text',{x:labelX,y:4,'text-anchor':anchor});label.textContent=note.id;
      const title=svgElement('text',{class:'node-title',x:labelX,y:19,'text-anchor':anchor});title.textContent=note.title.length>12?note.title.slice(0,12)+'…':note.title;
      const hint=svgElement('title',{});hint.textContent=`${note.id} ${note.title}\n${note.availability}`;
      node.append(circle,label,title,hint);$('nodes').append(node);
      node.addEventListener('pointerdown',e=>startDrag(e,note.id));
      node.addEventListener('pointerenter',()=>{hovered=note.id;highlightGraph();});
      node.addEventListener('pointerleave',()=>{hovered=null;highlightGraph();});
      node.addEventListener('focus',()=>{hovered=note.id;highlightGraph();});
      node.addEventListener('blur',()=>{hovered=null;highlightGraph();});
      node.addEventListener('click',e=>{if(moved&&e.detail>0)e.preventDefault();else emphasized=note.id;moved=false;highlightGraph();});
      node.addEventListener('keydown',e=>{if(e.key===' '){e.preventDefault();emphasized=note.id;location.hash=note.id;highlightGraph();}});
      return {id:note.id,element:node};
    });
    paint();highlightGraph();restartSimulation(.2);
  }

  function paint() {
    positions=Object.fromEntries(simulationNodes.map(p=>[p.id,{x:width/2+(p.x-worldCenter.x)*fitScale,y:plotCenterY+(p.y-worldCenter.y)*fitScale}]));
    for(const {edge,element} of edgeElements){const a=positions[edge.source],b=positions[edge.target];element.setAttribute('x1',a.x);element.setAttribute('y1',a.y);element.setAttribute('x2',b.x);element.setAttribute('y2',b.y);}
    for(const {id,element} of nodeElements){const p=positions[id],radius=nodeRadius(id),right=p.x>width*.68;element.setAttribute('transform',`translate(${p.x},${p.y})`);element.querySelector('circle').setAttribute('r',radius);for(const label of element.querySelectorAll('text')){label.setAttribute('x',right?-radius-5:radius+5);label.setAttribute('text-anchor',right?'end':'start');}}
    for(const {element} of edgeElements){element.style.strokeWidth=String(settings.lineSizeMultiplier*1.1);element.setAttribute('marker-end',settings.showArrow?'url(#arrow)':'');}
    $('camera').setAttribute('transform',`translate(${panX},${panY}) scale(${zoom})`);
    const focus=hovered||emphasized;
    const labelOpacity=focus?Math.max(.12,Math.min(1,zoom*Math.pow(2,settings.textFadeMultiplier/4))):1;
    for(const {id,element} of nodeElements)for(const label of element.querySelectorAll('text'))label.style.opacity=String(id===focus?1:labelOpacity);
  }

  function highlightGraph() {
    const focus=hovered||emphasized;
    const connected = new Set([focus]);
    for(const edge of edges)if(edge.source===focus||edge.target===focus){connected.add(edge.source);connected.add(edge.target);}
    for(const {id,element} of nodeElements){element.classList.toggle('selected',id===focus);element.classList.toggle('dimmed',!!focus&&!connected.has(id));}
    for(const {edge,element} of edgeElements){const active=edge.source===focus||edge.target===focus;element.classList.toggle('active',active);element.classList.toggle('dimmed',!!focus&&!active);}
    paint();
  }

  function resetView(){zoom=1;panX=0;panY=0;paint();}
  function scaleBy(factor){automaticFit=false;const next=Math.max(.25,Math.min(5,zoom*factor)),ratio=next/zoom;panX=width/2-(width/2-panX)*ratio;panY=height/2-(height/2-panY)*ratio;zoom=next;paint();}
  function startDrag(e,id){if(e.button!==0)return;e.stopPropagation();moved=false;automaticFit=false;const point=id?pointCache.get(id):null;dragging={id,x:e.clientX,y:e.clientY,panX,panY,start:point?{x:point.x,y:point.y}:null};if(point){point.fx=point.x;point.fy=point.y;restartSimulation(.3);}$('graph').setPointerCapture(e.pointerId);}
  $('graph').addEventListener('pointerdown',e=>startDrag(e,null));
  $('graph').addEventListener('pointermove',e=>{if(!dragging)return;const dx=e.clientX-dragging.x,dy=e.clientY-dragging.y;if(Math.hypot(dx,dy)>5)moved=true;if(dragging.id){const p=pointCache.get(dragging.id);p.x=p.fx=dragging.start.x+dx/zoom/fitScale;p.y=p.fy=dragging.start.y+dy/zoom/fitScale;}else{panX=dragging.panX+dx;panY=dragging.panY+dy;}paint();});
  function finishDrag(e){const current=dragging;dragging=null;if($('graph').hasPointerCapture(e.pointerId))$('graph').releasePointerCapture(e.pointerId);if(current?.id){const point=pointCache.get(current.id);point.fx=point.fy=null;restartSimulation(.3);if(!moved&&e.type!=='pointercancel'){emphasized=current.id;location.hash=current.id;highlightGraph();}}else if(current&&!moved&&e.type!=='pointercancel'){emphasized=hovered=null;highlightGraph();}}
  $('graph').addEventListener('pointerup',finishDrag);
  $('graph').addEventListener('pointercancel',finishDrag);
  $('graph').addEventListener('wheel',e=>{if(e.ctrlKey)return;e.preventDefault();scaleBy(Math.exp(-e.deltaY*.002));},{passive:false});
  $('graph').setAttribute('tabindex','0');
  $('graph').addEventListener('keydown',e=>{if(['+','=','-','ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();if(e.key==='+'||e.key==='=')scaleBy(1.25);else if(e.key==='-')scaleBy(.8);else{automaticFit=false;const amount=e.shiftKey?60:20;panX+=e.key==='ArrowLeft'?amount:e.key==='ArrowRight'?-amount:0;panY+=e.key==='ArrowUp'?amount:e.key==='ArrowDown'?-amount:0;paint();}}});
  $('zoom-in').addEventListener('click',()=>scaleBy(1.25));$('zoom-out').addEventListener('click',()=>scaleBy(.8));
  $('reset-graph').addEventListener('click',()=>{fitWorld();resetView();emphasized=hovered=null;highlightGraph();});
  $('pause-layout').addEventListener('click',()=>{if($('graph').dataset.running==='true'){userPaused=true;stopSimulation();}else{userPaused=false;restartSimulation();}});
  $('note-list').addEventListener('click',e=>{const link=e.target.closest('[data-note]');if(link){emphasized=link.dataset.note;highlightGraph();}});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'){emphasized=hovered=null;highlightGraph();}});
  function showSettings(){for(const input of document.querySelectorAll('[data-setting]')){if(input.type==='checkbox')input.checked=settings[input.dataset.setting];else{input.value=settings[input.dataset.setting];input.previousElementSibling.value=String(settings[input.dataset.setting]);}}}
  function saveSettings(){try{localStorage.setItem(settingsKey,JSON.stringify(settings));}catch(_){} }
  for(const input of document.querySelectorAll('[data-setting]'))input.addEventListener('input',()=>{settings[input.dataset.setting]=input.type==='checkbox'?input.checked:Number(input.value);showSettings();saveSettings();if(['centerStrength','repelStrength','linkStrength','linkDistance','nodeSizeMultiplier'].includes(input.dataset.setting)){applyForces();restartSimulation();}paint();});
  $('restore-settings').addEventListener('click',()=>{settings={...sharedSettings};saveSettings();showSettings();applyForces();restartSimulation();paint();});
  $('settings-origin').textContent='Obsidianの保存設定を引継ぎ（'+new Intl.DateTimeFormat('ja-JP').format(new Date(data.graph_settings.source_saved_at))+'）';
  showSettings();
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stopSimulation();});
  window.addEventListener('pagehide',stopSimulation);
  $('main-scope').addEventListener('click',()=>{scope='main';renderIndex();if(notes[selected].scope==='detail')location.hash='T01';});
  $('detail-scope').addEventListener('click',()=>{scope='detail';renderIndex();});
  $('search').addEventListener('input',e=>{search=e.target.value;renderIndex();});
  $('side').addEventListener('change',e=>{side=e.target.value;renderIndex();});
  $('detail-content').addEventListener('click',e=>{const link=e.target.closest('a[href^="#heading="]');if(link){e.preventDefault();scrollHeading(decodeURIComponent(link.hash.slice(9)));}});
  window.addEventListener('hashchange',()=>{const id=location.hash.slice(1);emphasized=notes[id]?id:null;hovered=null;route();highlightGraph();if(matchMedia('(max-width:850px)').matches)$('detail').scrollIntoView({block:'start'});});
  let resizeFrame;
  new ResizeObserver(()=>{cancelAnimationFrame(resizeFrame);resizeFrame=requestAnimationFrame(renderGraph);}).observe($('graph'));
  renderIndex();route();
})();
