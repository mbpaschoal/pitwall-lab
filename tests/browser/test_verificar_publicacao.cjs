/* Real browser counterexamples: broken image, wrong identity and wrong bytes. */
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const {verifyImage,expectations,verifyDeployment,ready,inspectControls}=require('./verificar_publicacao.cjs');
const root=path.resolve(__dirname,'../../distribuicao/pitwall-dashboard');
const catalog=JSON.parse(fs.readFileSync(path.join(root,'static/pitwall-media/catalog.json'))).method;
const variant=catalog.variants[0],raw=fs.readFileSync(path.join(root,variant.path));
const digest=crypto.createHash('sha256').update(raw).digest('hex');
let browser;
test.before(async()=>{const options={headless:true};if(process.env.PLAYWRIGHT_CHANNEL)options.channel=process.env.PLAYWRIGHT_CHANNEL;browser=await chromium.launch(options);});
test.after(async()=>{await browser?.close();});
async function withPage(action){const context=await browser.newContext();try{await action(await context.newPage());}finally{await context.close();}}

test('an approved photograph must decode and retain its SHA',async()=>withPage(async page=>{
 await page.setContent('<img class="fan-hero-image" src="data:image/webp;base64,'+raw.toString('base64')+'">');
 const result=await verifyImage(page,page,{sha256:digest});
 assert.equal(result.decoded,true);assert.equal(result.width,variant.width);assert.equal(result.sha256,variant.sha256);
}));
test('a valid image with another identity is rejected',async()=>withPage(async page=>{
 await page.setContent('<img class="fan-hero-image" src="data:image/webp;base64,'+raw.toString('base64')+'">');
 await assert.rejects(verifyImage(page,page,{sha256:'0'.repeat(64)}),{code:'integrity'});
}));
test('a failed image is not accepted merely because its element exists',async()=>withPage(async page=>{
 await page.route('https://blocked.invalid/**',route=>route.abort());
 await page.setContent('<img class="fan-hero-image" src="https://blocked.invalid/photo.webp">');
 await assert.rejects(verifyImage(page,page,{sha256:digest}));
 assert.equal(await page.locator('.fan-hero-image').count(),1);
}));
test('language and ready controls are checked against the supplied argument',async()=>withPage(async page=>{
 for(const lang of ['pt','en']){
  await page.setContent('<html lang="'+lang+'"><body><div class="stApp" data-test-script-state="notRunning">v0.8.27</div><section class="fan-hero"><h1>Fixture</h1></section><div class="st-key-journey-navigation"><div role="radiogroup">'+Array(6).fill('<label>Fixture</label>').join('')+'</div></div><div class="st-key-journey-context-row"><div data-testid="stSelectbox"></div><div data-testid="stSelectbox"></div></div><div class="st-key-pw_language_button_page_pt"><button>PT</button></div><div class="st-key-pw_language_button_page_en"><button>EN</button></div></body></html>');
  await ready(page,'0.8.27',lang);
 }
}));
function linkFixture(lang){
 const screens=['Corridas','Pilotos','Campeonato','Previsões','Desempenho','Metodologia'];
 return '<html lang="'+lang+'"><head><meta charset="utf-8"></head><body><div class="stApp" data-test-script-state="notRunning">v0.8.27</div><section class="fan-hero"><h1>Fixture</h1></section><nav class="journey-navigation-fallback">'+screens.map(s=>'<a data-screen="'+s+'" href="?tela='+encodeURIComponent(s)+'&lang='+lang+'">'+s+'</a>').join('')+'</nav><div class="st-key-journey-context-row"><div data-testid="stSelectbox"></div><div data-testid="stSelectbox"></div></div>'+['pt','en'].map(l=>'<a class="pw-language-fallback" data-language="'+l+'" href="?lang='+l+'">'+l+'</a>').join('')+'</body></html>';
}
test('a changed URL cannot admit the previous route photograph',async()=>withPage(async page=>{
 await page.route('https://fixture.invalid/**',route=>route.fulfill({status:200,contentType:'text/html',body:linkFixture('pt')}));
 await page.goto('https://fixture.invalid/?tela=Metodologia&lang=pt');
 await page.locator('.fan-hero').evaluate(e=>e.dataset.heroKind='race');
 await ready(page,'0.8.27','pt');
 const pending=ready(page,'0.8.27','pt','Metodologia');
 assert.equal(await Promise.race([pending.then(()=> 'admitted'),page.waitForTimeout(250).then(()=> 'waiting')]),'waiting');
 await page.locator('.fan-hero').evaluate(e=>e.dataset.heroKind='method');
 assert.equal((await pending).ready,true);
}));
test('wrapped React Aria radio controls remain native and usable',async()=>withPage(async page=>{
 await page.setContent('<html lang="pt"><body><div class="stApp" data-test-script-state="notRunning">v0.8.27</div><section class="fan-hero"><h1>Fixture</h1></section><div class="st-key-journey-navigation"><div role="radiogroup">'+Array(6).fill('<div><label>Fixture</label></div>').join('')+'</div></div><div class="st-key-journey-context-row"><div data-testid="stSelectbox"></div><div data-testid="stSelectbox"></div></div><div class="st-key-pw_language_button_page_pt"><button>PT</button></div><div class="st-key-pw_language_button_page_en"><button>EN</button></div></body></html>');
 const state=await ready(page,'0.8.27','pt');assert.equal(state.navigation,'native');
}));
test('usable link alternatives are admitted in both languages',async()=>withPage(async page=>{
 for(const lang of ['pt','en']){
  await page.route('https://fixture.invalid/**',route=>route.fulfill({status:200,contentType:'text/html',body:linkFixture(lang)}));
  await page.goto('https://fixture.invalid/?lang='+lang);
  const state=await ready(page,'0.8.27',lang);
  assert.equal(state.navigation,'links');assert.equal(state.language_control,'links');
  await page.unroute('https://fixture.invalid/**');
 }
}));
test('hidden, foreign or duplicate links cannot replace usable controls',async()=>withPage(async page=>{
 await page.route('https://fixture.invalid/**',route=>route.fulfill({status:200,contentType:'text/html',body:linkFixture('pt')}));
 await page.goto('https://fixture.invalid/?lang=pt');
 const inspect=()=>page.locator('body').evaluate(inspectControls,'pt');
 assert.equal((await inspect()).ready,true);
 await page.locator('.journey-navigation-fallback').evaluate(e=>e.style.display='none');
 assert.equal((await inspect()).ready,false);
 await page.locator('.journey-navigation-fallback').evaluate(e=>e.style.display='');
 await page.locator('.journey-navigation-fallback>a').first().evaluate(e=>e.href='https://foreign.invalid/?tela=Corridas&lang=pt');
 assert.equal((await inspect()).ready,false);
 await page.locator('.journey-navigation-fallback>a').first().evaluate(e=>e.href='?tela=Corridas&lang=pt');
 await page.locator('.pw-language-fallback[data-language=en]').evaluate(e=>{e.dataset.language='pt';e.href='?lang=pt';});
 assert.equal((await inspect()).ready,false);
 await page.locator('.pw-language-fallback').last().evaluate(e=>{e.dataset.language='en';e.href='?lang=en';});
 await page.locator('body').evaluate(e=>e.insertAdjacentHTML('beforeend','<div data-testid="stAlertContentError">Unrecovered widget failure</div>'));
 await assert.rejects(ready(page,'0.8.27','pt'),{code:'integrity'});
}));
test('a foreign static source is rejected even if it serves the expected pixels',async()=>withPage(async page=>{
 await page.route('https://foreign.invalid/**',route=>route.fulfill({status:200,contentType:'image/webp',body:raw}));
 await page.setContent('<img class="fan-hero-image" src="https://foreign.invalid/photo.webp">');
 await assert.rejects(verifyImage(page,page,{sha256:digest,variants:[variant]}),{code:'integrity'});
}));
test('calendar, circuit and version must belong to the package',()=>{
 const version=fs.readFileSync(path.join(root,'VERSION'),'utf8').trim();
 const state=JSON.parse(fs.readFileSync(path.join(root,'frontend_assets/operacao_fim_semana.json')));
 assert.match(expectations(root,version,[state.temporada,state.rodada,state.circuito_id]).build,/^[a-f0-9]{64}$/);
 assert.throws(()=>expectations(root,version,[2026,20,'americas']),{code:'integrity'});
 assert.throws(()=>expectations(root,'0.0.0',[2026,20,'interlagos']),{code:'integrity'});
});
test('a rejected package produces a failure receipt before network access',async()=>{
 const tmp=fs.mkdtempSync(path.join(require('node:os').tmpdir(),'pitwall-preflight-'));
 try{
  const state=JSON.parse(fs.readFileSync(path.join(root,'frontend_assets/operacao_fim_semana.json')));
  const input=path.join(tmp,'event.json');fs.writeFileSync(input,JSON.stringify({identidade:[state.temporada,state.rodada,state.circuito_id]}));
  await assert.rejects(verifyDeployment('0.0.0',input,path.join(tmp,'out')),{code:'integrity'});
  const receipt=JSON.parse(fs.readFileSync(path.join(tmp,'out/publication.json')));
  assert.equal(receipt.status,'failed');assert.equal(receipt.stage,'preflight');assert.deepEqual(receipt.cases,[]);
 }finally{fs.rmSync(tmp,{recursive:true,force:true});}
});
