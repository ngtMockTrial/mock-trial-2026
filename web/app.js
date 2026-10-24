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
  let scope = query.get('scope') === 'detail' ? 'detail' : 'main';
  let selected = 'T01', search = query.get('q') || '', side = query.get('side') || '';
  let nodeElements = [], edgeElements = [], visible = [], edges = [], positions = {};
  let width = 600, height = 800, zoom = 1, panX = 0, panY = 0;
  let dragging = null, moved = false;
  const ns = 'http://www.w3.org/2000/svg';
  const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const sourceURL = path => data.repository + '/blob/main/' + path.split('/').map(encodeURIComponent).join('/');
  $('repository').href = data.repository;
  $('search').value = search;
  $('side').value = side;

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

  function simulate(ids) {
    const points = ids.map((id,i) => ({id, x:500+Math.cos(i*2.39996)*Math.sqrt(i+1)*37, y:420+Math.sin(i*2.39996)*Math.sqrt(i+1)*37}));
    const map = Object.fromEntries(points.map(p => [p.id,p]));
    for (let step=0; step<230; step++) {
      const force = Object.fromEntries(points.map(p => [p.id,{x:(500-p.x)*.015,y:(420-p.y)*.02}]));
      for (let i=0; i<points.length; i++) for (let j=i+1; j<points.length; j++) {
        const a=points[i], b=points[j], dx=a.x-b.x || .1, dy=a.y-b.y || .1;
        const d2=Math.max(200, dx*dx+dy*dy), d=Math.sqrt(d2), repulsion=4300/d2;
        force[a.id].x+=dx/d*repulsion; force[a.id].y+=dy/d*repulsion;
        force[b.id].x-=dx/d*repulsion; force[b.id].y-=dy/d*repulsion;
      }
      for (const edge of edges) {
        const a=map[edge.source],b=map[edge.target],dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy)||1;
        const spring=(d-125)*.025;
        force[a.id].x+=dx/d*spring;force[a.id].y+=dy/d*spring;
        force[b.id].x-=dx/d*spring;force[b.id].y-=dy/d*spring;
      }
      for (const p of points) {p.x+=Math.max(-8,Math.min(8,force[p.id].x));p.y+=Math.max(-8,Math.min(8,force[p.id].y));}
    }
    if (!points.length) return {};
    const minX=Math.min(...points.map(p=>p.x)),maxX=Math.max(...points.map(p=>p.x)),minY=Math.min(...points.map(p=>p.y)),maxY=Math.max(...points.map(p=>p.y));
    const sx=(width-100)/Math.max(maxX-minX,1),sy=(height-220)/Math.max(maxY-minY,1),scale=Math.min(sx,sy);
    return Object.fromEntries(points.map(p=>[p.id,{x:width/2+(p.x-(minX+maxX)/2)*scale,y:height/2+20+(p.y-(minY+maxY)/2)*scale}]));
  }

  function svgElement(tag, attributes) {
    const element = document.createElementNS(ns, tag);
    for (const [key,value] of Object.entries(attributes)) element.setAttribute(key,value);
    return element;
  }

  function renderGraph() {
    const rect = $('graph').getBoundingClientRect(); width=rect.width; height=rect.height;
    $('graph').setAttribute('viewBox',`0 0 ${width} ${height}`);
    const ids=visible.map(n=>n.id),set=new Set(ids);
    edges=data.edges.filter(e=>set.has(e.source)&&set.has(e.target));
    positions=simulate(ids);
    $('graph-count').textContent=`${ids.length}点・${edges.length}接続`;
    $('edges').replaceChildren();$('nodes').replaceChildren();
    edgeElements=edges.map(edge=>{
      const line=svgElement('line',{class:'edge','data-field':edge.field,'marker-end':'url(#arrow)'});
      const title=svgElement('title',{});title.textContent=`${edge.source} → ${edge.target}：${names[edge.field]}`;line.append(title);$('edges').append(line);
      return {edge,element:line};
    });
    nodeElements=visible.map(note=>{
      const node=svgElement('a',{href:'#'+note.id,class:'graph-node'+(warningStates.has(note.state)?' warning':''),'data-node':note.id,'aria-label':`${note.id} ${note.title}、${note.side}、${note.kind}`,tabindex:0});
      const radius={1:5,2:7,3:10,4:14,5:22}[note.priority]||7;
      const circle=svgElement('circle',{r:radius,fill:note.id==='T00'?'#9bd0ff':bright[note.side]});
      const alignRight=positions[note.id].x>width*.68;
      const labelX=alignRight ? -radius-5 : radius+5;
      const anchor=alignRight?'end':'start';
      const label=svgElement('text',{x:labelX,y:4,'text-anchor':anchor});label.textContent=note.id;
      const title=svgElement('text',{class:'node-title',x:labelX,y:19,'text-anchor':anchor});title.textContent=note.title.length>12?note.title.slice(0,12)+'…':note.title;
      const hint=svgElement('title',{});hint.textContent=`${note.id} ${note.title}\n${note.availability}`;
      node.append(circle,label,title,hint);$('nodes').append(node);
      node.addEventListener('pointerdown',e=>startDrag(e,note.id));
      node.addEventListener('click',e=>{if(moved){e.preventDefault();moved=false;}});
      node.addEventListener('keydown',e=>{if(e.key===' '){e.preventDefault();location.hash=note.id;}});
      return {id:note.id,element:node};
    });
    resetView();paint();highlightGraph();
  }

  function paint() {
    for(const {edge,element} of edgeElements){const a=positions[edge.source],b=positions[edge.target];element.setAttribute('x1',a.x);element.setAttribute('y1',a.y);element.setAttribute('x2',b.x);element.setAttribute('y2',b.y);}
    for(const {id,element} of nodeElements){const p=positions[id];element.setAttribute('transform',`translate(${p.x},${p.y})`);}
    $('camera').setAttribute('transform',`translate(${panX},${panY}) scale(${zoom})`);
  }

  function highlightGraph() {
    const connected = new Set([selected]);
    for(const edge of edges)if(edge.source===selected||edge.target===selected){connected.add(edge.source);connected.add(edge.target);}
    for(const {id,element} of nodeElements){element.classList.toggle('selected',id===selected);element.classList.toggle('dimmed',!connected.has(id));}
    for(const {edge,element} of edgeElements){const active=edge.source===selected||edge.target===selected;element.classList.toggle('active',active);element.classList.toggle('dimmed',!active);}
  }

  function resetView(){zoom=1;panX=0;panY=0;paint();}
  function scaleBy(factor){const next=Math.max(.4,Math.min(3,zoom*factor)),ratio=next/zoom;panX=width/2-(width/2-panX)*ratio;panY=height/2-(height/2-panY)*ratio;zoom=next;paint();}
  function startDrag(e,id){if(e.button!==0)return;e.stopPropagation();moved=false;dragging={id,x:e.clientX,y:e.clientY,panX,panY,start: id?{...positions[id]}:null};$('graph').setPointerCapture(e.pointerId);}
  $('graph').addEventListener('pointerdown',e=>startDrag(e,null));
  $('graph').addEventListener('pointermove',e=>{if(!dragging)return;const dx=e.clientX-dragging.x,dy=e.clientY-dragging.y;if(Math.hypot(dx,dy)>5)moved=true;if(dragging.id){positions[dragging.id]={x:dragging.start.x+dx/zoom,y:dragging.start.y+dy/zoom};}else{panX=dragging.panX+dx;panY=dragging.panY+dy;}paint();});
  $('graph').addEventListener('pointerup',e=>{const current=dragging;dragging=null;if($('graph').hasPointerCapture(e.pointerId))$('graph').releasePointerCapture(e.pointerId);if(current?.id&&!moved){location.hash=current.id;}});
  $('graph').addEventListener('pointercancel',()=>{dragging=null;});
  $('zoom-in').addEventListener('click',()=>scaleBy(1.25));$('zoom-out').addEventListener('click',()=>scaleBy(.8));
  $('reset-graph').addEventListener('click',()=>{resetView();for(const {element} of nodeElements)element.classList.remove('dimmed');for(const {element} of edgeElements)element.classList.remove('dimmed');});
  $('main-scope').addEventListener('click',()=>{scope='main';renderIndex();if(notes[selected].scope==='detail')location.hash='T01';});
  $('detail-scope').addEventListener('click',()=>{scope='detail';renderIndex();});
  $('search').addEventListener('input',e=>{search=e.target.value;renderIndex();});
  $('side').addEventListener('change',e=>{side=e.target.value;renderIndex();});
  $('detail-content').addEventListener('click',e=>{const link=e.target.closest('a[href^="#heading="]');if(link){e.preventDefault();scrollHeading(decodeURIComponent(link.hash.slice(9)));}});
  window.addEventListener('hashchange',()=>{route();if(matchMedia('(max-width:850px)').matches)$('detail').scrollIntoView({block:'start'});});
  let resizeFrame;
  new ResizeObserver(()=>{cancelAnimationFrame(resizeFrame);resizeFrame=requestAnimationFrame(renderGraph);}).observe($('graph'));
  renderIndex();route();
})();
