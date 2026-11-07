/* Editorial shell in the actual Streamlit scrollport, including native input. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const pw=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const [base,output]=process.argv.slice(2);assert(base&&output,'Usage: URL OUTPUT');fs.mkdirSync(output,{recursive:true});
const engine=process.env.PLAYWRIGHT_BROWSER||'chromium';
const widths=process.env.PITWALL_FINISH_WIDTHS?process.env.PITWALL_FINISH_WIDTHS.split(',').map(Number):[1440,1024,768,390,320];
const pointerMouse=process.env.PITWALL_FINISH_POINTER==='mouse';
async function ready(app){
 await app.evaluate(()=>window.pwFinishIdle=0);
 await app.waitForFunction(()=>{
  if(document.querySelector('.stApp')?.dataset.testScriptState!=='notRunning'||document.querySelector('.st-key-pw-sidebar-menu details')?.dataset.pwReady!=='true'){window.pwFinishIdle=0;return false}
  window.pwFinishIdle ||= performance.now();return performance.now()-window.pwFinishIdle>=500;
 },null,{timeout:90000});
 await app.evaluate(()=>document.fonts.ready);
 await app.waitForFunction(()=>![...document.querySelectorAll('[data-testid=stSkeleton]')].some(e=>{const r=e.getBoundingClientRect();return r.width&&r.height&&r.top<innerHeight&&r.bottom>0}),null,{timeout:30000});
 await app.locator('.pc-photo').evaluateAll(xs=>Promise.all(xs.map(x=>x.decode())));
 await app.waitForTimeout(200);
}
(async()=>{
 const options={headless:true};if(engine==='chromium'&&process.env.PLAYWRIGHT_CHANNEL)options.channel=process.env.PLAYWRIGHT_CHANNEL;
 const browser=await pw[engine].launch(options),report={base,engine,cases:[]};
 const save=()=>fs.writeFileSync(path.join(output,'acceptance.json'),JSON.stringify(report,null,2));
 try{for(const width of widths)for(const lang of ['pt','en']){
  const context=await browser.newContext({viewport:{width,height:1000},isMobile:width<600&&!pointerMouse,hasTouch:width<600&&!pointerMouse,reducedMotion:width===320?'reduce':'no-preference'});
  const page=await context.newPage(),errors=[],row={width,lang};page.on('pageerror',e=>errors.push(e.message));report.cases.push(row);
  try{
   await page.goto(base+'/?'+new URLSearchParams({tela:'Corridas',aba:'Tempos',temporada:2026,gp:4,lang}));
   const app=await require('./app_surface.cjs').surface(page,base);
   await ready(app);
   row.geometry=await app.evaluate(()=>{
    const rect=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,bottom:r.bottom}};
    const search=[...document.querySelectorAll('.st-key-global-search button')].find(e=>e.getBoundingClientRect().width);
    return {h1:[...document.querySelectorAll('h1')].map(e=>e.textContent),duplicate:!!document.querySelector('.pw-location'),overflow:document.documentElement.scrollWidth>innerWidth+1,search:rect(search),fields:[...document.querySelectorAll('.st-key-journey-context-row [role=group]')].map(rect),language:rect(document.querySelector('[class*=st-key-pw_language_switch_]'))};
   });
   const g=row.geometry;assert.equal(g.h1.length,1);assert.equal(g.duplicate,false);assert.equal(g.overflow,false);
   assert(g.fields.length===2&&g.fields.every(r=>r.height>=44)&&g.search.height>=44);
   const centers=[...g.fields,g.search].map(r=>r.y+r.height/2);assert(Math.max(...centers)-Math.min(...centers)<=1,'Context axes differ');
   if(width<801){
    const menu=await require('./sidebar_navigation.cjs').openMenu(app);
    const targets=await app.locator('.st-key-pw-sidebar-menu button').evaluateAll(xs=>xs.map(e=>{const r=e.getBoundingClientRect();return {x:r.x,right:r.right,width:r.width,height:r.height}}));
    assert.equal(targets.length,15);assert(targets.every(r=>r.height>=44&&r.width>=44&&r.x>=0&&r.right<=width+1),'Narrow navigation target is clipped or smaller than 44 px');
    await menu.locator('summary').click();
   }
   await app.locator('.stMain').evaluate(e=>e.scrollTo({top:650,behavior:'instant'}));
   const scrolled=await app.locator('[class*=st-key-pw_language_switch_]').boundingBox();assert(Math.abs(scrolled.y-g.language.y)<=1,'Language does not follow scroll');
   await app.locator('.stMain').evaluate(e=>e.scrollTo({top:0,behavior:'instant'}));
   const search=app.locator('.st-key-global-search').getByRole('button',{name:lang==='pt'?'Buscar':'Search',exact:true});
   await search.focus();await page.keyboard.press('Enter');
   const input=app.getByRole('textbox',{name:lang==='pt'?'Buscar no Pitwall Lab':'Search Pitwall Lab',exact:true});await input.waitFor();await input.fill(lang==='pt'?'voltas':'laps');await input.press('Enter');
   await app.locator('[data-testid=stPopoverBody]').getByText(lang==='pt'?'Sessões e voltas':'Sessions and laps',{exact:true}).waitFor();await ready(app);await page.keyboard.press('Escape');
   await app.locator('[data-testid=stPopoverBody]').waitFor({state:'hidden'});
   await app.locator('.stMain').evaluate(e=>e.scrollTo({top:0,behavior:'instant'}));
   await page.screenshot({path:path.join(output,width+'-'+lang+'-sessions.png')});
   if(width===390){
    await app.evaluate(()=>document.documentElement.style.fontSize='200%');
    assert.equal(await app.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false,'Enlarged text overflows');
    const valueFits=await app.locator('.st-key-journey-context-row [role=combobox]').first().evaluate(e=>{
     const style=getComputedStyle(e),canvas=document.createElement('canvas'),context=canvas.getContext('2d');
     context.font=[style.fontStyle,style.fontWeight,style.fontSize,style.fontFamily].join(' ');
     const available=e.clientWidth-parseFloat(style.paddingLeft)-parseFloat(style.paddingRight);
     return context.measureText(e.value||e.textContent).width<=available+1;
    });assert(valueFits,'Enlarged selected year is clipped');
    await page.screenshot({path:path.join(output,width+'-'+lang+'-enlarged.png')});
    await app.evaluate(()=>document.documentElement.style.removeProperty('font-size'));
   }
   await require('./sidebar_navigation.cjs').choose(app,'forecast');
   await app.waitForFunction(()=>new URL(location.href).searchParams.get('tela')==='Previsões',null,{timeout:15000});await ready(app);
   // Switch within the native GP selector; a current event without an emission
   // must not acquire the recorded Mexico prediction by retaining widget state.
   await app.locator('.st-key-journey-context-row [role=combobox]').nth(1).click();
   await app.getByRole('option',{name:lang==='pt'?'19 — México':'19 — Mexico',exact:true}).click();
   await app.waitForFunction(()=>new URL(location.href).searchParams.get('gp')==='19',null,{timeout:15000});await ready(app);
   const opener=app.getByRole('button',{name:lang==='pt'?'Ver as cartas deste GP':'See the cards for this GP',exact:true});
   const o=await opener.boundingBox();assert(o&&o.y+o.height<=1000,'Primary card action falls below first viewport');
   assert.equal(await app.locator('.pw-sealed-deck:visible').count(),0,'Cards must open in the dialog');
   const credit=app.locator('.pc-credits summary');await credit.click();assert(await app.locator('.pc-credits[open]').isVisible());
   assert((await app.locator('.pc-credits').innerText()).includes(lang==='pt'?'Arte editorial original':'Original Pitwall Lab'));await credit.click();
   await app.locator('.stMain').evaluate(e=>e.scrollTo({top:0,behavior:'instant'}));
   await page.screenshot({path:path.join(output,width+'-'+lang+'-forecast.png')});
   if(pointerMouse&&width<801){
    let transitions=0;
    for(let repeat=0;repeat<3;repeat++)for(const [id,key,value] of [['sessions','aba','Tempos'],['strategy','aba','Estratégias'],['forecast','tela','Previsões'],['sources','secao','fontes']]){
     await require('./sidebar_navigation.cjs').choose(app,id);
     await app.waitForFunction(({key,value})=>new URL(location.href).searchParams.get(key)===value&&document.querySelector('.stApp')?.dataset.testScriptState==='notRunning',{key,value},{timeout:15000});
     await ready(app);
     assert.equal(new URL(await app.locator('body').evaluate(()=>location.href)).searchParams.get('gp'),'19');
     transitions++;
    }
    row.native_mouse_transitions=transitions;
   }
   if(width===390){
    await require('./sidebar_navigation.cjs').choose(app,'profiles');await ready(app);
    const portrait=app.locator('.fan-hero-portrait .fan-hero-real-portrait');
    if(await portrait.count()){
     const h=await app.locator('.fan-hero h1').boundingBox(),p=await portrait.boundingBox();
     assert(h.x+h.width<=p.x+1,'Profile title overlaps the portrait');
     await page.screenshot({path:path.join(output,width+'-'+lang+'-profile.png')});
    }
   }
   assert.equal(context.pages().length,1);assert.deepEqual(errors,[]);row.status='passed';
  }catch(e){row.status='failed';row.error=e.stack;await page.screenshot({path:path.join(output,width+'-'+lang+'-failed.png')});throw e}
  finally{save();await context.close()}
  console.log(JSON.stringify(row));
 }}finally{await browser.close();save()}
})().catch(e=>{console.error(e);process.exit(1)});
