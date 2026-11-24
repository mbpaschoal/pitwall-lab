/* All-team Cars journey. Read-only UI and download checks, no new inference. */
const fs = require('node:fs'), path = require('node:path'), assert = require('node:assert/strict');
const pw = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const {surface} = require('./app_surface.cjs');
const [base, output] = process.argv.slice(2);
assert(base && output, 'Usage: aceite_carros.cjs URL OUTPUT');
const engine = process.env.PLAYWRIGHT_BROWSER || 'chromium';
assert(['chromium','webkit'].includes(engine));
const out = path.resolve(output);
fs.mkdirSync(out, {recursive:true});
const evidence = {base, engine, scope:'observed browser journey', protocol:'Independent deep-link setup uses fresh tabs; native interactions stay in place. All pageerrors across live tabs are retained and rejected.', cases:[]};

// BackMsg field 11 requests a Streamlit script rerun; ignore other traffic.
function requestsRerun(payload) {
 const b = Buffer.isBuffer(payload) ? payload : Buffer.from(payload); let i = 0;
 function uint() { let n=0,s=0,v; do { assert(i<b.length && s<=49); v=b[i++]; n+=(v&127)*2**s; s+=7; } while(v&128); return n; }
 while(i<b.length) {
  const tag=uint(), field=Math.floor(tag/8), wire=tag%8;
  if(field===11) return true;
  if(wire===0) uint(); else if(wire===1) i+=8; else if(wire===2) { const n=uint(); i+=n; }
  else if(wire===5) i+=4; else return false;
 }
 return false;
}

function url(year, round, lang) {
 const target = new URL(base);
 target.search = new URLSearchParams({tela:'Carros',temporada:year,gp:round,lang});
 return target.href;
}

async function ready(app) {
 await app.waitForFunction(()=>{
  const ok = document.querySelector('.stApp')?.dataset.testScriptState === 'notRunning'
   && document.querySelector('.st-key-pw-sidebar-menu details')?.dataset.pwReady === 'true';
  if (!ok) { window.carsSettledAt = 0; return false; }
  window.carsSettledAt ||= performance.now();
  return performance.now()-window.carsSettledAt > 350;
 }, null, {timeout:45000});
 await app.evaluate(()=>document.fonts.ready);
 assert.equal(await app.locator('[data-testid=stException]').count(), 0);
 if (process.env.PITWALL_EXPECTED_VERSION)
  await app.getByText('v'+process.env.PITWALL_EXPECTED_VERSION,{exact:true}).waitFor();
}

async function activate(control, touch) {
 if (touch) await control.tap(); else await control.click();
}

async function view(app, label, touch) {
 await activate(app.locator('.st-key-car_view label').filter({hasText:new RegExp('^'+label+'$')}),touch);
 await ready(app);
}

async function capture(page, app, name) {
 await app.locator('.stMain').evaluate(e=>e.scrollTop=0);
 await page.screenshot({path:path.join(out,name+'.png'),fullPage:true});
 return name+'.png';
}

async function run() {
 const browser = await pw[engine].launch({headless:true});
 try {
  for (const width of [1440,390]) for (const lang of ['pt','en']) {
   const touch = width === 390;
   const context = await browser.newContext({viewport:{width,height:1000},isMobile:touch,hasTouch:touch});
   let page = await context.newPage(); const errors = []; let reruns = 0;
   const pendingResources = new Set();
   function track(target) {
    target.on('request',request=>{if (/\/(?:component|media|static\/js)\//.test(new URL(request.url()).pathname)) pendingResources.add(request);});
    target.on('requestfinished',request=>pendingResources.delete(request));
    target.on('requestfailed',request=>pendingResources.delete(request));
    target.on('websocket',ws=>{if(ws.url().includes('_stcore/stream')) ws.on('framesent',event=>{if(requestsRerun(event.payload)) reruns++;});});
    target.on('pageerror',error=>errors.push(error.message));
   }
   track(page);
   const row = {width,lang,states:[],screenshots:[],setupPages:0};
   evidence.cases.push(row);
   async function open(year, round) {
    const deadline = Date.now()+30000; let settledSince = 0;
    while (Date.now()<deadline) {
     if (pendingResources.size) settledSince = 0;
     else {settledSince ||= Date.now(); if (Date.now()-settledSince>=500) break;}
     await page.waitForTimeout(50);
    }
    assert.equal(pendingResources.size,0,'Finish component/media loads before opening an independent case');
    // These URLs set up independent cases, not user navigation. Keep old tabs observed.
    if (page.url()!=='about:blank') {page=await context.newPage(); track(page);}
    row.setupPages++;
    await page.goto(url(year,round,lang));
   }
   try {
    await open(2026,21);
    let app = await surface(page,base);
    await app.getByRole('heading',{name:lang==='pt'?'Carros':'Cars',level:1,exact:true}).waitFor({timeout:45000});
    await ready(app);
    assert.equal(await app.locator('.st-key-pw-sidebar-menu button').count(),16);
    assert.equal(await app.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    assert.equal(await app.locator('#carros-comparativo').count(),1);
    row.states.push('all_team_comparison');
    row.screenshots.push(await capture(page,app,`comparison-${width}-${lang}`));

    if (touch) {
     await page.setViewportSize({width,height:560});
     await app.locator('.stMain').evaluate(m=>m.scrollTo({top:.25*(m.scrollHeight-m.clientHeight),behavior:'instant'}));
     const sensitivity=app.locator('.st-key-car_no_flags');
     const checkbox=sensitivity.getByRole('checkbox');
     const explanation=app.getByText(lang==='pt'
      ? 'Sensibilidade conservadora: um alerta local na sessão não prova que o piloto encontrou a bandeira.'
      : 'Conservative sensitivity: a local flag in the session does not prove the driver encountered it.',{exact:true});
     await explanation.waitFor({state:'visible'});
     await sensitivity.locator('label').tap(); await ready(app);
     assert.equal(await checkbox.isChecked(),true);
     await sensitivity.locator('label').tap(); await ready(app);
     assert.equal(await checkbox.isChecked(),false);
     row.states.push('small_viewport_sensitivity_touch_and_visible_explanation');
     await page.setViewportSize({width,height:1000});
    }

    await view(app,lang==='pt'?'Evolução':'Evolution',touch);
    await app.locator('[data-testid=stPlotlyChart] svg.main-svg').first().waitFor({timeout:30000});
    assert.equal(await app.locator('.js-plotly-plot').evaluate(e=>e.data.length),11);
    assert.equal(await app.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    row.states.push('all_team_evolution');
    row.screenshots.push(await capture(page,app,`evolution-${width}-${lang}`));
    await app.locator('[data-testid=stPlotlyChart]').scrollIntoViewIfNeeded();
    await page.screenshot({path:path.join(out,`chart-complete-${width}-${lang}.png`),fullPage:true});

    await view(app,lang==='pt'?'Alterações':'Updates',touch);
    await app.getByRole('link',{name:lang==='pt'?'Ler declaração da FIA':'Read FIA declaration',exact:true}).waitFor();
    row.states.push('declared_components_and_source');
    row.screenshots.push(await capture(page,app,`updates-${width}-${lang}`));
    await activate(app.getByText(lang==='pt'?'Método, fontes e download':'Method, sources and download',{exact:true}),touch);
    const button = app.getByRole('button',{name:lang==='pt'?'Baixar dados do comparativo':'Download comparison data',exact:true});
    await button.evaluate(e=>e.scrollIntoView({block:'center'}));
    await button.click({trial:true});
    row.downloadTarget = await button.evaluate(e=>{const r=e.getBoundingClientRect(), hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2); return {visible:!!hit&&(hit===e||e.contains(hit)),label:e.textContent};});
    assert.equal(row.downloadTarget.visible,true);
    const beforeDownload = reruns;
    const [download] = await Promise.all([
     page.waitForEvent('download'),
     activate(button,touch)
    ]);
    const bytes = fs.readFileSync(await download.path()), asset = JSON.parse(bytes);
    assert.equal(await download.failure(),null);
    await page.waitForTimeout(700);
    assert.equal(reruns,beforeDownload,'Downloading the Cars snapshot must preserve the current view');
    row.downloadReruns=reruns-beforeDownload;
    assert.equal(asset.events.length,21);
    assert.equal(Object.keys(asset.teams).length,11);
    assert.equal(asset.forecast_input,false);
    const miami = asset.events.find(e=>e.round===4);
    assert.equal(miami.teams.find(t=>t.team_id==='red_bull').q1.gap_percent,null);
    if (process.env.PITWALL_SOURCE_ROOT)
     assert(bytes.equals(fs.readFileSync(path.join(process.env.PITWALL_SOURCE_ROOT,'frontend_assets/car_comparison_2026.json'))));
    row.states.push('download_exact_snapshot_and_missingness');

    if (!touch) {
     await open(2026,7);
     app = await surface(page,base); await ready(app);
     await view(app,lang==='pt'?'Alterações':'Updates',false);
     await app.locator('.st-key-car_update_team [role=combobox]').click();
     await app.getByRole('option',{name:'Racing Bulls',exact:true}).click(); await ready(app);
     await app.getByText(lang==='pt'
      ? 'O título desta seção da equipe diverge do GP do documento. A associação dos componentes ao evento aguarda revisão.'
      : 'This team section has a different GP title from the document. Component association with the event is awaiting review.',{exact:true}).waitFor();
     assert.equal(await app.locator('[data-testid=stDataFrame]').count(),0);
     row.states.push('conflicting_event_identity_withheld');
     row.screenshots.push(await capture(page,app,`pending-${lang}`));

     await open(2026,4);
     app = await surface(page,base); await ready(app);
     await view(app,lang==='pt'?'Alterações':'Updates',false);
     await app.getByText((lang==='pt'?'Software SECU divulgado: ':'Published SECU software: ')+'SR1830 + B127.',{exact:true}).waitFor();
     row.states.push('published_secu_version');
    }

    await open(2024,1);
    app = await surface(page,base); await ready(app);
    await app.getByText(lang==='pt'
     ? 'O comparativo de carros cobre a temporada 2026. Selecione 2026 para consultar as onze equipes; os outros anos permanecem sem dados nesta seção.'
     : 'Car comparison covers 2026. Select 2026 to view all eleven teams; other years have no data in this section.',{exact:true}).waitFor();
    assert.equal(await app.locator('[data-testid=stDataFrame]').count(),0);
    row.states.push('unsupported_season_empty_state');
    assert.deepEqual(errors,[]);
    row.pageerrors=errors; row.status='passed';
    console.log(JSON.stringify({engine,width,lang,status:row.status,states:row.states}));
   } catch (error) {
    row.status='failed'; row.error=String(error); row.pageerrors=errors;
    await page.screenshot({path:path.join(out,`failure-${width}-${lang}.png`),fullPage:true}).catch(()=>{});
    throw error;
   } finally {
    await context.close();
    fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify(evidence,null,2));
   }
  }
 } finally { await browser.close(); }
}

run().catch(error=>{console.error(error);process.exitCode=1;});
