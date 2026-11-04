const fs=require('node:fs'),path=require('node:path');
const {chromium}=require('/Users/MBPaschoal/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const output=process.argv[2],report={start_utc:new Date().toISOString(),console:[],failures:[],resources:[],samples:[]};
 const browser=await chromium.launch({headless:true,channel:'chrome',args:['--disable-http2']});
 const context=await browser.newContext({viewport:{width:1440,height:1000}}),page=await context.newPage();
 page.on('console',m=>{if(['error','warning'].includes(m.type()))report.console.push({type:m.type(),text:m.text()});});
 page.on('pageerror',e=>report.console.push({type:'pageerror',text:e.message}));
 page.on('requestfailed',r=>{const u=new URL(r.url());if(/\.(js|css|woff2?)(\?|$)/.test(u.pathname))report.failures.push({path:u.pathname,error:r.failure()?.errorText});});
 page.on('response',r=>{const u=new URL(r.url());if(/\.(js|css|woff2?)$/.test(u.pathname))report.resources.push({path:u.pathname,status:r.status(),type:r.headers()['content-type']});});
 try{
  await page.goto('https://pitwall-lab.streamlit.app/?tela=Metodologia&temporada=2026&gp=19&lang=pt',{waitUntil:'domcontentloaded',timeout:45000});
  for(let i=0;i<6;i++){
   await page.waitForTimeout(10000);
   const f=page.frames().find(f=>f.url().includes('/~/+/'));
   report.samples.push({utc:new Date().toISOString(),frame_found:!!f,...(f?await f.evaluate(()=>({language:document.documentElement.lang,state:document.querySelector('.stApp')?.dataset.testScriptState,nav:document.querySelectorAll('.st-key-journey-navigation [role=radiogroup]>label').length,selects:document.querySelectorAll('.st-key-journey-context-row [data-baseweb=select]').length,placeholders:document.querySelectorAll('[data-testid=stSkeleton]').length,title:document.querySelector('.fan-hero h1')?.textContent,version:Array.from(document.querySelectorAll('span')).find(e=>/^v0\.8\.28$/.test(e.textContent))?.textContent,body_classes:document.body.className,nav_html:document.querySelector('.st-key-journey-navigation')?.outerHTML.slice(0,3500)})):{} )});
  }
  await page.screenshot({path:path.join(output,'focused-method.jpg'),type:'jpeg',quality:80});
 }catch(e){report.error=e.message;}finally{report.end_utc=new Date().toISOString();fs.writeFileSync(path.join(output,'focused-diagnostic.json'),JSON.stringify(report,null,2));await browser.close();console.log(JSON.stringify({samples:report.samples,failures:report.failures,console:report.console,resources_failed:report.resources.filter(r=>r.status>=400)}));}
})();
