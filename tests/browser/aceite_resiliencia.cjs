/* PT/EN: real navigation and language clicks with native Radio/Button unavailable. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const {inspectControls}=require('./verificar_publicacao.cjs');
const base=process.argv[2]||'http://127.0.0.1:8501';
const output=path.resolve(process.argv[3]||'/tmp/pitwall-resilience');
const screens=['Corridas','Pilotos','Campeonato','Previsões','Desempenho','Metodologia'];
async function check(page,lang){
 await page.locator('.journey-navigation-fallback').waitFor({state:'visible',timeout:30000});
 await page.waitForFunction(lang=>document.documentElement.lang===lang&&document.querySelector('.stApp')?.dataset.testScriptState==='notRunning',lang,{timeout:30000});
 assert.equal(await page.locator('.journey-navigation-fallback>a:visible').count(),6);
 assert.equal(await page.locator('.pw-language-fallback:visible').count(),2);
 assert.equal(await page.locator('.st-key-journey-navigation [role=radiogroup]').count(),0);
 assert.equal(await page.locator('[data-testid=stException]').count(),0);
 assert.equal(await page.locator('.st-key-journey-navigation [role=alert]:visible,[class*=st-key-pw_language_cell_] [role=alert]:visible').count(),0,'Recovered controls must not announce an unusable widget error');
 const state=await page.locator('body').evaluate(()=>({query:Object.fromEntries(new URL(location.href).searchParams),overflow:document.documentElement.scrollWidth>innerWidth+1,targets:[...document.querySelectorAll('.journey-navigation-fallback>a,.pw-language-fallback')].map(e=>({width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height}))}));
 assert.equal(state.query.gp,'19');assert.equal(state.query.temporada,'2026');assert.equal(state.query.lang,lang);assert.equal(state.overflow,false);
 assert.ok(state.targets.every(t=>t.width>=44&&t.height>=44),'Every link needs a 44px target');
 assert.ok(await page.locator('.pw-language-fallback:visible').evaluateAll(es=>es.every(e=>getComputedStyle(e).textDecorationLine==='none')),'Flag links must match the native flags without underlining');
 return state;
}
(async()=>{fs.mkdirSync(output,{recursive:true});const options={headless:true};if(process.env.PLAYWRIGHT_CHANNEL)options.channel=process.env.PLAYWRIGHT_CHANNEL;
 const browser=await chromium.launch(options),report={base,utc:new Date().toISOString(),cases:[]};
 try{for(const width of [1440,390])for(const lang of ['pt','en']){
  const context=await browser.newContext({viewport:{width,height:1000},deviceScaleFactor:2,isMobile:width===390,hasTouch:width===390});
  const page=await context.newPage(),row={width,lang,blocked:[],visited:[]};report.cases.push(row);
  await page.route(/\/static\/js\/(?:Radio|Button)\.[^/?]+\.js(?:\?|$)/,route=>{row.blocked.push(new URL(route.request().url()).pathname);return route.abort();});
  try{
   await page.goto(base+'/?tela=Corridas&temporada=2026&gp=19&lang='+lang,{waitUntil:'domcontentloaded'});
   await check(page,lang);
   await page.screenshot({path:path.join(output,`${width}-${lang}-fallback.jpg`),type:'jpeg',quality:80});
   for(const screen of screens){
    const link=page.locator('.journey-navigation-fallback>a[data-screen="'+screen+'"]');
    await link.focus();assert.equal(await link.evaluate(e=>e===document.activeElement),true);
    await page.keyboard.press('Enter');await page.waitForURL(u=>u.searchParams.get('tela')===screen);
    const state=await check(page,lang);assert.equal(state.query.tela,screen);row.visited.push(screen);
   }
   const other=lang==='pt'?'en':'pt';await page.locator('.pw-language-fallback[data-language="'+other+'"]').click();
   await page.waitForURL(u=>u.searchParams.get('lang')===other);await check(page,other);
   await page.locator('.fan-hero h1').filter({hasText:other==='en'?'How it works':'Como funciona'}).waitFor();
   row.language_switched=other;assert.ok(row.blocked.length>=2);row.status='passed';
  }catch(e){row.status='failed';row.error=e.message;throw e;}
  finally{fs.writeFileSync(path.join(output,'resilience.json'),JSON.stringify(report,null,2));await context.close();}
  console.log(JSON.stringify({width,lang,status:row.status,visited:row.visited.length,blocked:row.blocked.length}));
 }
 const recovery=await browser.newContext({viewport:{width:1440,height:1000}}),page=await recovery.newPage(),releases=[];
 try{
  await page.route(/\/static\/js\/(?:Radio|Button)\.[^/?]+\.js(?:\?|$)/,async route=>{await new Promise(resolve=>releases.push(resolve));await route.continue();});
  await page.goto(base+'/?tela=Metodologia&temporada=2026&gp=19&lang=pt',{waitUntil:'domcontentloaded'});
  await check(page,'pt');const last=page.locator('.journey-navigation-fallback>a').last();await last.focus();
  assert.ok(releases.length>=2);releases.forEach(resolve=>resolve());
  await page.waitForFunction(()=>document.querySelectorAll('.st-key-journey-navigation [role=radiogroup] label').length===6);
  assert.equal(await last.evaluate(e=>e===document.activeElement),true,'Hydration must preserve keyboard focus');
  assert.equal((await page.locator('body').evaluate(inspectControls,'pt')).navigation,'links');
  await page.keyboard.press('Tab');
  const deadline=Date.now()+10000;let state;
  do{state=await page.locator('body').evaluate(inspectControls,'pt');if(state.navigation==='native'&&state.language_control==='native')break;await page.waitForTimeout(100);}while(Date.now()<deadline);
  assert.equal(state.navigation,'native');assert.equal(state.language_control,'native');
  assert.equal(await page.locator('.journey-navigation-fallback>a:visible,.pw-language-fallback:visible').count(),0);
  report.late_hydration={status:'passed',focus_preserved:true,native_controls_restored:true};
 }finally{releases.forEach(resolve=>resolve());await recovery.close();}
 }finally{await browser.close();report.completed_at_utc=new Date().toISOString();fs.writeFileSync(path.join(output,'resilience.json'),JSON.stringify(report,null,2));}
})().catch(e=>{console.error(e);process.exitCode=1;});
