/* Real sidebar, reveal, context and responsive acceptance. No data mutations. */
const fs = require('node:fs'), path = require('node:path'), assert = require('node:assert/strict');
const pw = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const [base, output] = process.argv.slice(2);
assert(base && output, 'Usage: aceite_sidebar.cjs URL OUTPUT');
fs.mkdirSync(output, {recursive:true});
const engine = process.env.PLAYWRIGHT_BROWSER || 'chromium';
const routes = {
 forecast:{tela:'Previsões'}, accuracy:{tela:'Desempenho'}, summary:{tela:'Corridas',aba:'Visão geral'},
 sessions:{tela:'Corridas',aba:'Tempos'}, strategy:{tela:'Corridas',aba:'Estratégias'},
 weather:{tela:'Corridas',aba:'Clima'}, history:{tela:'Corridas',aba:'Histórico'},
 teams:{tela:'Corridas',aba:'Comparativo de equipes'}, profiles:{tela:'Pilotos',visao:'perfil'},
 duel:{tela:'Pilotos',visao:'duelo'}, 'drivers-standing':{tela:'Campeonato',painel:'pilotos'},
 'teams-standing':{tela:'Campeonato',painel:'equipes'}, method:{tela:'Metodologia'},
 sources:{tela:'Metodologia',secao:'fontes'}, terms:{tela:'Metodologia',secao:'termos'}
};
async function surface(page) {
 if (!base.includes('streamlit.app')) return page;
 for (let n=0;n<120;n++) { const frame=page.frames().find(f=>f.url().includes('/~/+/'));if(frame)return frame;await page.waitForTimeout(250); }
 throw Error('Missing app frame');
}
async function ready(page, expected) {
 const app=await surface(page);
 await app.evaluate(()=>window.sidebarIdleSince=0);
 await app.waitForFunction(expected=>{
  const q=new URL(location.href).searchParams;
  const valid = document.querySelector('.stApp')?.dataset.testScriptState==='notRunning' &&
   document.querySelectorAll('.st-key-pw-sidebar-menu button').length===15 &&
   document.querySelector('.st-key-pw-sidebar-menu details')?.dataset.pwReady==='true' &&
   Object.entries(expected).every(([key,value])=>q.get(key)===String(value)) &&
   document.documentElement.lang===q.get('lang');
  if(!valid){window.sidebarIdleSince=0;return false;}
  window.sidebarIdleSince ||= performance.now();
  return performance.now()-window.sidebarIdleSince>700;
 },expected,{timeout:45000});
 await app.evaluate(()=>document.fonts.ready);
 assert.equal(await app.locator('[data-testid="stException"]').count(),0);
 return app;
}
async function choose(page,id) {
 const app=await surface(page), details=app.locator('.st-key-pw-sidebar-menu details');
 if (!await details.evaluate(e=>e.open)) {
  if(await details.locator('summary').isVisible())await details.locator('summary').click();
  else await app.waitForFunction(()=>document.querySelector('.st-key-pw-sidebar-menu details')?.open===true);
 }
 const button=app.locator('.st-key-pw_nav_'+id+' button');
 await button.click();
 return ready(page,routes[id]);
}
async function run() {
 const options={headless:true};if(engine==='chromium'&&process.env.PLAYWRIGHT_CHANNEL)options.channel=process.env.PLAYWRIGHT_CHANNEL;
 const browser=await pw[engine].launch(options), report={base,engine,cases:[]};
 try { for(const width of [1440,390])for(const lang of ['pt','en']) {
  const context=await browser.newContext({viewport:{width,height:1000},isMobile:width===390,hasTouch:width===390});
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  const legacy=width===1440&&lang==='pt';
  if(legacy)await page.addInitScript(()=>{
   window.legacyBridge={refresh:()=>{window.legacyRefreshCount=(window.legacyRefreshCount||0)+1;}};
   window.__pitwallMotion=window.legacyBridge;
  });
  const row={width,lang,visited:[]};report.cases.push(row);
  try {
   await page.goto(base+'/?'+new URLSearchParams({temporada:2025,gp:1,tela:'Corridas',lang}));
   let app=await ready(page,{temporada:2025,gp:1,tela:'Corridas',lang});
   const marker=await app.evaluate(()=>window.sidebarAcceptanceMarker=crypto.randomUUID());
   let extraPages=0;context.on('page',()=>extraPages++);
   for(const id of Object.keys(routes)) {
    const start=performance.now();app=await choose(page,id);
    const q=new URL(app.url()).searchParams;
    assert.equal(q.get('gp'),'1');assert.equal(q.get('temporada'),'2025');
    assert.equal(q.get('lang'),lang);assert.equal(await app.evaluate(()=>window.sidebarAcceptanceMarker),marker);
    assert.equal(await app.locator('.journey-calendar:visible,.fan-gp-tabs:visible,.st-key-journey-navigation:visible').count(),0);
    if(['sessions','strategy','weather','history','teams'].includes(id))assert.equal(await app.locator('.pw-postcard').count(),0);
    if(id==='teams-standing')assert.equal(await app.locator('#campeonato-completo').count(),0);
    if(width===390)await app.waitForFunction(()=>document.querySelector('.st-key-pw-sidebar-menu details')?.open===false);
    row.visited.push({id,ready_ms:performance.now()-start});
   }
   app=await choose(page,'forecast');
   assert.equal(await app.locator('.pw-sealed-card').count(),0);
   const before=await app.locator('body').ariaSnapshot();
   assert(!/Lando Norris|Max Verstappen|George Russell/.test(before),'Unrevealed identities in accessibility tree');
   await app.getByRole('button',{name:lang==='pt'?'Ver as cartas deste GP':'See the cards for this GP',exact:true}).click();
   await app.locator('.pw-sealed-deck').waitFor();
   assert.equal(await app.locator('.pw-card-back:visible').count(),3);
   assert.equal(await app.locator('.st-key-forecast-details:visible').count(),0);
   await app.locator('[data-tarot-reveal]').first().focus();await page.keyboard.press('Enter');
   await app.locator('.pw-revealed-face:visible').waitFor();
   assert.equal(await app.locator('.pw-card-back:visible').count(),2);
   assert.equal(await app.locator('.st-key-forecast-details:visible').count(),0);
   const deck=await app.locator('[data-deck-key]').getAttribute('data-deck-key');
   await choose(page,'sessions');app=await choose(page,'forecast');
   await app.waitForFunction(()=>document.querySelectorAll('.pw-revealed-face:not([hidden])').length===1);
   assert.equal(await app.locator('[data-deck-key]').getAttribute('data-deck-key'),deck);
   for(const i of [1,2])await app.locator('.pw-sealed-card').nth(i).locator('[data-tarot-reveal]').click();
   await app.locator('.st-key-forecast-details').waitFor({state:'visible'});
   await app.waitForFunction(()=>[...document.querySelectorAll('.pw-revealed-face')].every(e=>!e.hidden&&e.getAnimations().every(a=>a.playState==='finished')));
   assert.equal(await app.locator('.pw-revealed-face:visible').count(),3);
   const other=lang==='pt'?'en':'pt';await app.getByRole('button',{name:other==='pt'?'🇧🇷 Português':'🇬🇧 English',exact:true}).click();
   app=await ready(page,{tela:'Previsões',temporada:2025,gp:1,lang:other});
   await app.waitForFunction(()=>document.querySelectorAll('.pw-revealed-face:not([hidden])').length===3);
   await app.waitForFunction(()=>document.querySelectorAll('.pw-revealed-face:not([hidden]) [data-tarot-hide]').length===3 && [...document.querySelectorAll('.pw-revealed-face')].every(e=>e.getBoundingClientRect().height>100));
   assert.equal(await app.locator('[data-deck-key]').getAttribute('data-deck-key'),deck,'Language changed deck identity');
   for(const w of [width,320]) {
    await page.setViewportSize({width:w,height:1000});
    assert.equal(await app.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false,'Horizontal overflow');
   }
   await page.setViewportSize({width,height:1000});
   await page.screenshot({path:path.join(output,engine+'-'+width+'-'+lang+'.png')});
   assert.equal(extraPages,0);assert.deepEqual(errors,[]);
   if(legacy)assert(await app.evaluate(()=>window.__pitwallMotion===window.legacyBridge&&!!window.__pitwallEditorial),'New features did not install beside the existing motion bridge');
   row.status='passed';row.same_document=true;row.new_tabs=extraPages;row.individual_reveal=true;row.language_keeps_reveal=true;
  } catch(error) { row.status='failed';row.error=error.stack;await page.screenshot({path:path.join(output,engine+'-'+width+'-'+lang+'-failed.png')}); }
  finally {await context.close();fs.writeFileSync(path.join(output,'sidebar.json'),JSON.stringify(report,null,2));}
  console.log(JSON.stringify({width,lang,status:row.status,error:row.error?.split('\n')[0]}));
 }} finally {await browser.close();}
 assert(report.cases.length===4&&report.cases.every(r=>r.status==='passed'),'Sidebar acceptance failed');
}
run().catch(error=>{console.error(error);process.exitCode=1;});
