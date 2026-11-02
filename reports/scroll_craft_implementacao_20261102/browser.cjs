const {chromium}=require('/Users/MBPaschoal/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const out=__dirname;const rows=[];
(async()=>{let b=await chromium.launch({channel:'chrome',headless:true});try{
for(const width of [390,1440])for(const lang of ['pt','en'])for(const reduce of [false,true]){
 const c=await b.newContext({viewport:{width,height:900},isMobile:width===390,hasTouch:width===390,reducedMotion:reduce?'reduce':'no-preference'}),p=await c.newPage();
 await p.addInitScript(()=>{window.motionCalls=0;const original=Element.prototype.animate;Element.prototype.animate=function(...args){if(this.classList.contains('fan-process-step'))window.motionCalls++;return original.apply(this,args)}});
 const activate=async locator=>width===390?locator.tap():locator.click();
 const errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto('http://127.0.0.1:8632/?tela=Metodologia&temporada=2026&gp=19&lang='+lang);
 await p.locator('.fan-process-step').last().waitFor();await p.waitForFunction(()=>window.__pitwallMotion&&document.querySelector('.stApp')?.dataset.testScriptState==='notRunning');
 await p.waitForTimeout(600);
 assert.equal(await p.locator('[data-testid=stException]').count(),0);
 assert.equal(await p.evaluate(()=>window.motionCalls),reduce?0:3);
 assert.equal(await p.locator('[data-pw-motion]').isDisabled(),reduce);
 if(reduce)assert.equal(await p.locator('[data-pw-motion]').innerText(),lang==='pt'?'Movimento reduzido pelo sistema':'System reduced motion');
 const style=await p.locator('.stMain').evaluate(n=>getComputedStyle(n).scrollBehavior);assert.equal(style,reduce?'auto':'smooth');
 const initial=p.url();const link=p.locator('[data-pw-scroll]').first();await link.focus();await p.keyboard.press('Enter');await p.waitForTimeout(600);
 assert.equal(await p.evaluate(()=>document.activeElement.id),'pw-main-content');assert.equal(p.url(),initial);
 await activate(p.locator('[data-pw-scroll]').nth(1));await p.waitForTimeout(600);assert.equal(await p.evaluate(()=>document.activeElement.id),'pw-page-top');assert.equal(await p.locator('.stMain').evaluate(n=>n.scrollTop),0);
 if(!reduce){await activate(p.locator('[data-pw-motion]'));assert.equal(await p.locator('[data-pw-motion]').innerText(),lang==='pt'?'Ativar movimento':'Enable motion');assert.equal(await p.locator('.stMain').evaluate(n=>getComputedStyle(n).scrollBehavior),'auto');await activate(p.locator('[data-pw-motion]'));}
 for(let i=0;i<6;i++){
  await activate(p.locator('.st-key-journey-navigation [role=radiogroup]>label').nth(i));
  await p.waitForFunction(()=>document.querySelector('.stApp')?.dataset.testScriptState==='notRunning');await p.waitForTimeout(400);
  assert.equal(await p.locator('[data-testid=stException]').count(),0);assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
 }
 assert.equal(await p.evaluate(()=>window.motionCalls),reduce?0:3,'Method entrance repeated after navigation');
 assert.equal(await p.locator('.pw-page-tools').count(),1);
 assert(p.url().includes('gp=19')&&p.url().includes('temporada=2026')&&p.url().includes('lang='+lang),p.url());
 assert.deepEqual(errors,[]);
 await p.screenshot({path:path.join(out,`${lang}-${width}-${reduce}.jpg`),type:'jpeg',quality:75,scale:'css'});
 rows.push({lang,width,reducedMotion:reduce,screens:6,entrances:reduce?0:3,status:'passed'});fs.writeFileSync(path.join(out,'browser.json'),JSON.stringify(rows,null,2));console.log(rows.at(-1));await c.close();
}
}finally{await b.close()}})().catch(e=>{console.error(e);process.exit(1)});
