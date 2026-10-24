// Bundled Playwright; validates the generated local file without an HTTP server.
const { chromium } = require('C:/Users/ryupc/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const path = require('path');
const fs = require('fs');
const { pathToFileURL } = require('url');
const assert = require('assert/strict');
(async () => {
  const browser = await chromium.launch({channel:'msedge',headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1080}});
    const errors=[]; page.on('pageerror',e=>errors.push(String(e)));
    const root=path.resolve(__dirname,'..');
    const url=pathToFileURL(path.join(root,'検討','つながりをたどる.html')).href;
    await page.goto(url+'#R01');
    assert.equal(await page.locator('#index .index-item').count(),43);
    for(const [area,ids] of Object.entries({inputs:['F03','E10'],outputs:['R02'],objections:['D01'],questions:['Q01']})) {
      assert.deepEqual(await page.locator('#'+area+' [data-open]').evaluateAll(es=>es.map(e=>e.dataset.open)),ids);
    }
    assert.match(await page.locator('#current').innerText(),/条件付き/);
    const output=path.join(__dirname,'構造化確認');fs.mkdirSync(output,{recursive:true});
    await page.screenshot({path:path.join(output,'接続画面_PC.png'),fullPage:true});
    await page.locator('#inputs [data-open="F03"]').click();
    assert.match(await page.locator('#current').innerText(),/F03/);
    await page.locator('#back').click();
    assert.match(await page.locator('#current').innerText(),/R01/);
    await page.locator('#search').fill('zzzz-no-match');
    assert.equal(await page.locator('#index .index-item').count(),0);
    await page.locator('#search').fill('眼鏡');
    assert.ok(await page.locator('#index .index-item').count()>0);
    await page.locator('#search').fill('');
    await page.locator('#kind').selectOption('供述獲得候補');
    assert.equal(await page.locator('#index .index-item').count(),2);
    await page.locator('#index [data-open="W01"]').click();
    assert.match(await page.locator('#current').innerText(),/まだ証拠ではない/);
    assert.equal(await page.locator('#outputs [data-open]').count(),0);
    assert.match(await page.locator('#extras').innerText(),/現在は利用不可/);
    await page.locator('#kind').selectOption('');
    await page.locator('#index [data-open="E07"]').click();
    assert.match(await page.locator('#current').innerText(),/採否留保/);
    await page.locator('#body-details summary').click();
    assert.ok((await page.locator('#body').innerText()).includes('変更記録'));
    await page.goto(url+'#R01');
    await page.setViewportSize({width:390,height:844});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:path.join(output,'接続画面_スマホ.png'),fullPage:true});
    await page.locator('#inputs [data-open="F03"]').click();
    assert.match(await page.locator('#current').innerText(),/F03/);
    assert.equal(errors.length,0,errors.join('\n'));
    console.log('PASS: relations, pending/candidate distinction, search, filters, navigation, body, desktop/mobile, no browser errors');
  } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exitCode=1;});
