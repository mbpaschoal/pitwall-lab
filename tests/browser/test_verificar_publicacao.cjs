/* Real browser counterexamples: broken image, wrong identity and wrong bytes. */
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const {verifyImage,expectations,ready}=require('./verificar_publicacao.cjs');
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
  await page.setContent('<html lang="'+lang+'"><body><div class="stApp" data-test-script-state="notRunning">v0.8.27</div><section class="fan-hero"><h1>Fixture</h1></section><div class="st-key-journey-navigation"><div role="radiogroup">'+Array(6).fill('<label>Fixture</label>').join('')+'</div></div><div class="st-key-journey-context-row"><div data-baseweb="select"></div><div data-baseweb="select"></div></div></body></html>');
  await ready(page,'0.8.27',lang);
 }
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
