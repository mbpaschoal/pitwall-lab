const fs=require('node:fs'),path=require('node:path');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{const out=process.argv[2];fs.mkdirSync(out,{recursive:true});const b=await chromium.launch({headless:true,channel:'chrome'});try{
const c=await b.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});const p=await c.newPage();
await p.goto('https://pitwall-lab.streamlit.app/?tela=Metodologia&temporada=2026&gp=20&lang=en',{waitUntil:'domcontentloaded',timeout:60000});
const a=p.frameLocator('iframe[src*="/~/+/"]').first();await a.getByText('v0.8.27',{exact:true}).waitFor({timeout:60000});
await a.locator('.stApp[data-test-script-state="notRunning"]').waitFor({timeout:30000});
const fonts=await a.locator('body').evaluate(async()=>{await Promise.race([document.fonts.ready,new Promise(r=>setTimeout(r,20000))]);return{status:document.fonts.status,material:[...document.fonts].filter(f=>/material/i.test(f.family)).map(f=>({family:f.family,status:f.status})),images:[...document.querySelectorAll('.fan-hero img')].map(e=>({source:e.currentSrc,complete:e.complete,width:e.naturalWidth,box:e.getBoundingClientRect().toJSON(),opacity:getComputedStyle(e).opacity,z:getComputedStyle(e).zIndex})),icons:[...document.querySelectorAll('[data-testid=stIconMaterial]')].map(e=>({text:e.innerText,font:getComputedStyle(e).fontFamily,width:e.getBoundingClientRect().width}))};});
await p.screenshot({path:path.join(out,'390-en-fonts-ready.png')});fs.writeFileSync(path.join(out,'fonts.json'),JSON.stringify({...fonts,utc:new Date().toISOString()},null,2));await c.close();
}finally{await b.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
