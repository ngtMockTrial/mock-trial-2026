const {chromium}=require('C:/Users/ryupc/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const path=require('path'),fs=require('fs'),assert=require('assert/strict');
const {pathToFileURL}=require('url');
(async()=>{
  const browser=await chromium.launch({channel:'msedge',headless:true});
  try {
    const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
    page.on('pageerror',e=>errors.push(String(e)));
    const root=path.resolve(__dirname,'..'),out=path.join(__dirname,'構造化確認');
    await page.goto(pathToFileURL(path.join(root,'検討/構造グラフ.html')).href);
    assert.equal(await page.locator('.tg-node').count(),43);
    const sizes=await page.locator('.tg-node').evaluateAll(es=>es.map(e=>[e.dataset.id,+e.dataset.radius]));
    assert.ok(sizes.filter(([id])=>id!=='T00').every(([,size])=>size<sizes.find(([id])=>id==='T00')[1]));
    assert.ok(sizes.find(([id])=>id==='T01')[1]>sizes.find(([id])=>id==='T02')[1]);
    await page.locator('[data-id="R01"]').click();
    assert.match(await page.locator('.tg-detail').innerText(),/条件付き/);
    for(const id of ['F03','E10','D01','Q01'])assert.match(await page.locator('.tg-detail').innerText(),new RegExp(id));
    await page.getByRole('combobox',{name:'立場',exact:true}).selectOption('弁護');
    assert.equal(await page.locator('.tg-node').count(),9);
    await page.getByRole('combobox',{name:'立場',exact:true}).selectOption('すべて');
    await page.getByRole('searchbox').fill('存在しない命題');assert.equal(await page.locator('.tg-node').count(),0);
    await page.getByRole('searchbox').fill('');
    await page.getByRole('combobox',{name:'種類',exact:true}).selectOption('供述獲得候補');
    assert.equal(await page.locator('.tg-node').count(),2);
    await page.locator('[data-id="W01"]').click();assert.match(await page.locator('.tg-detail').innerText(),/まだ証拠ではない/);
    await page.getByRole('combobox',{name:'種類',exact:true}).selectOption('すべて');
    await page.getByRole('button',{name:'選択解除',exact:true}).click();
    await page.locator('.tg-viewport').evaluate(e=>{e.scrollTop=0;});
    await page.screenshot({path:path.join(out,'構造グラフ_PC.png')});
    await page.locator('[data-id="R01"]').click();
    await page.screenshot({path:path.join(out,'構造グラフ_選択.png')});
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:path.join(out,'構造グラフ_狭幅.png'),fullPage:true});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    assert.deepEqual(errors,[]);
    console.log('PASS: 43ノート、個別サイズ、立場・種類フィルタ、未獲得表示、周辺接続、1440/390px');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
