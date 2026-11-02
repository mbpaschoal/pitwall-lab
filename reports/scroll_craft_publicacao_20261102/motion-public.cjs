const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const [base,out]=process.argv.slice(2);fs.mkdirSync(out,{recursive:true});const rows=[];
(async()=>{let b=await chromium.launch({channel:process.env.PLAYWRIGHT_CHANNEL||'chrome',headless:true});try{
for(const width of [390,1440])for(const lang of ['pt','en'])for(const reduce of [false,true]){
 const c=await b.newContext({viewport:{width,height:900},isMobile:width===390,hasTouch:width===390,reducedMotion:reduce?'reduce':'no-preference'}),p=await c.newPage();
 await p.addInitScript(()=>{window.motionCalls=0;const original=Element.prototype.animate;Element.prototype.animate=function(...args){if(this.classList.contains('fan-process-step'))window.motionCalls++;return original.apply(this,args)}});
 const activate=async locator=>width===390?locator.tap():locator.click();
 const errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto(base+'/?tela=Metodologia&temporada=2026&gp=19&lang='+lang,{timeout:90000});
 let surface=p;
 if(base.includes('streamlit.app')){for(let i=0;i<120;i++){surface=p.frames().find(f=>f.url().includes('/~/+/'));if(surface)break;await p.waitForTimeout(500)}assert(surface,'Public app frame unavailable');}
 await surface.locator('.fan-process-step').last().waitFor();await surface.waitForFunction(()=>window.__pitwallMotion&&document.querySelector('.stApp')?.dataset.testScriptState==='notRunning');
 await p.waitForTimeout(600);
 assert.equal(await surface.locator('[data-testid=stException]').count(),0);
 if(base.includes('streamlit.app'))assert((await surface.locator('body').innerText()).includes('v0.8.12'),'Wrong public version');
 assert.equal(await surface.evaluate(()=>window.motionCalls),reduce?0:3);
 assert.equal(await surface.locator('[data-pw-motion]').isDisabled(),reduce);
 if(reduce)assert.equal(await surface.locator('[data-pw-motion]').innerText(),lang==='pt'?'Movimento reduzido pelo sistema':'System reduced motion');
 assert.equal(await surface.locator('[data-pw-motion]').getAttribute('aria-pressed'),null,'Action button must not expose a contradictory toggle state');
 const toggleMotion=async()=>{let button=surface.locator('[data-pw-motion]');if(width===390)await button.tap();else{await button.focus();await p.keyboard.press('Space')}};
 const style=await surface.locator('.stMain').evaluate(n=>getComputedStyle(n).scrollBehavior);assert.equal(style,reduce?'auto':'smooth');
 const initial=surface.url();const link=surface.locator('[data-pw-scroll]').first();await link.focus();await p.keyboard.press('Enter');await p.waitForTimeout(600);
 assert.equal(await surface.evaluate(()=>document.activeElement.id),'pw-main-content');assert.equal(surface.url(),initial);
 await activate(surface.locator('[data-pw-scroll]').nth(1));await p.waitForTimeout(600);assert.equal(await surface.evaluate(()=>document.activeElement.id),'pw-page-top');assert.equal(await surface.locator('.stMain').evaluate(n=>n.scrollTop),0);
 if(!reduce){await toggleMotion();assert.equal(await surface.locator('[data-pw-motion]').innerText(),lang==='pt'?'Ativar movimento':'Enable motion');assert.equal(await surface.locator('.stMain').evaluate(n=>getComputedStyle(n).scrollBehavior),'auto');await toggleMotion();}
 for(let i=0;i<6;i++){
  await activate(surface.locator('.st-key-journey-navigation [role=radiogroup]>label').nth(i));
  await surface.waitForFunction(expected=>document.querySelector('.fan-hero')?.dataset.heroKind===expected && document.querySelector('.stApp')?.dataset.testScriptState==='notRunning' && document.body.innerText.includes('v0.8.12'),['race','drivers','championship','forecast','performance','method'][i],{timeout:60000});await p.waitForTimeout(500);
  assert.equal(await surface.locator('[data-testid=stException]').count(),0);
 if(base.includes('streamlit.app'))assert((await surface.locator('body').innerText()).includes('v0.8.12'),'Wrong public version');assert.equal(await surface.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
 }
 assert.equal(await surface.evaluate(()=>window.motionCalls),reduce?0:3,'Method entrance repeated after navigation');
 assert.equal(await surface.locator('.pw-page-tools').count(),1);
 assert(surface.url().includes('gp=19')&&surface.url().includes('temporada=2026')&&surface.url().includes('lang='+lang),surface.url());
 assert.deepEqual(errors,[]);
 await p.screenshot({path:path.join(out,`${lang}-${width}-${reduce}.jpg`),type:'jpeg',quality:75,scale:'css'});
 rows.push({lang,width,reducedMotion:reduce,screens:6,entrances:reduce?0:3,status:'passed'});fs.writeFileSync(path.join(out,'browser.json'),JSON.stringify(rows,null,2));console.log(rows.at(-1));await c.close();
}
}finally{await b.close()}})().catch(e=>{console.error(e);process.exit(1)});
