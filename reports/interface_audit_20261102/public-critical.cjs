/* Reproduce the user's two mobile collisions against the deployed build. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const manifest=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../distribuicao/pitwall-dashboard/MANIFESTO.json')));
const record={utc:new Date().toISOString(),version:manifest.versao_produto,build:manifest.apresentacao_build_sha256,cases:[]};
(async()=>{const browser=await chromium.launch({channel:process.env.PLAYWRIGHT_CHANNEL||'chrome',headless:true});try{
for(const width of [390,1440])for(const lang of ['pt','en']){
 const context=await browser.newContext({viewport:{width,height:844},isMobile:width===390,hasTouch:width===390}),page=await context.newPage();
 await page.goto('https://pitwall-lab.streamlit.app/?'+new URLSearchParams({tela:'Corridas',temporada:2026,gp:19,lang}),{waitUntil:'domcontentloaded',timeout:90000});
 let app;for(let i=0;i<120;i++){app=page.frames().find(f=>f.url().includes('/~/+/'));if(app)break;await page.waitForTimeout(500);}assert(app);
 await app.waitForFunction(({version,lang})=>document.querySelector('.stApp')?.dataset.testScriptState==='notRunning'&&document.documentElement.lang===lang&&document.querySelector('.fan-hero[data-hero-kind="race"]')&&document.querySelector('.st-key-journey-header')?.innerText.includes('v'+version),{version:manifest.versao_produto,lang},{timeout:120000});
 await app.evaluate(()=>document.fonts.ready);await page.waitForTimeout(700);
 const summary=app.locator('.st-key-race-summary');await summary.scrollIntoViewIfNeeded();await page.waitForTimeout(400);
 const geometry=await app.evaluate(()=>{const rect=s=>{const r=document.querySelector(s).getBoundingClientRect();return{top:r.top,bottom:r.bottom}};return {status:rect('.st-key-weekend-status'),summary:rect('.st-key-race-summary'),main:rect('.stMain'),dock:rect('.st-key-journey-navigation'),exceptions:document.querySelectorAll('[data-testid="stException"]').length,overflow:document.documentElement.scrollWidth>innerWidth+1}});
 assert(geometry.status.bottom<=geometry.summary.top);assert(geometry.main.bottom<=geometry.dock.top-4);assert.equal(geometry.exceptions,0);assert.equal(geometry.overflow,false);
 await page.screenshot({path:path.join(__dirname,`public-critical-${width}-${lang}.jpg`),type:'jpeg',quality:80});
 record.cases.push({width,lang,status:'passed',geometry,url:app.url()});await context.close();
}
}finally{await browser.close();fs.writeFileSync(path.join(__dirname,'public-critical.json'),JSON.stringify(record,null,2));}})().catch(e=>{console.error(e);process.exitCode=1});
