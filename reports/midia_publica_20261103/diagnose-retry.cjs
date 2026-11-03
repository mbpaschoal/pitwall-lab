/* Read-only diagnosis: no app DOM mutation and no personal/session headers saved. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const out=process.argv[2];fs.mkdirSync(out,{recursive:true});
(async()=>{const browser=await chromium.launch({headless:true,channel:'chrome'});const result={events:[],console:[]};try{
 const c=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});const p=await c.newPage();
 p.on('console',m=>{if(m.type()==='error'||m.type()==='warning')result.console.push(m.text().slice(0,1200));});
 p.on('request',r=>{if(r.url().includes('method-9776'))result.events.push({type:'request',url:r.url(),resource:r.resourceType(),utc:new Date().toISOString()});});
 p.on('requestfailed',r=>{if(r.url().includes('method-9776'))result.events.push({type:'failed',url:r.url(),error:r.failure()?.errorText});});
 p.on('response',async r=>{if(r.url().includes('method-9776'))result.events.push({type:'response',url:r.url(),status:r.status(),content_type:r.headers()['content-type']});});
 const url='https://pitwall-lab.streamlit.app/?tela=Metodologia&temporada=2026&gp=19&lang=pt';
 let app;
 for(let attempt=0;attempt<2;attempt++){
  await p.goto(url,{waitUntil:'domcontentloaded',timeout:60000});
  app=p.frameLocator('iframe[src*="/~/+/"]').first();
  try{await app.getByText('v0.8.27',{exact:true}).waitFor({timeout:45000});await app.locator('.fan-hero-image').waitFor({timeout:30000});break;}
  catch(e){if(attempt)throw e;result.bootstrap_retry=e.message.split('\n')[0];}
 }
 result.image=await app.locator('.fan-hero-image').evaluate(async e=>{
  const decoded=await Promise.race([e.decode().then(()=>true).catch(x=>String(x)),new Promise(r=>setTimeout(()=>r('timeout'),20000))]);
  return{decoded,src:e.src,currentSrc:e.currentSrc,srcset:e.srcset,complete:e.complete,natural:[e.naturalWidth,e.naturalHeight],base:document.baseURI,url:location.href,loading:e.loading,html:e.outerHTML,
   resources:performance.getEntriesByType('resource').filter(r=>r.name.includes('method-9776')).map(r=>({name:r.name,duration:r.duration,transfer:r.transferSize})),
   metas:[...document.querySelectorAll('meta[http-equiv]')].map(e=>({name:e.httpEquiv,value:e.content}))};
 });
 for(const target of [result.image.src,'https://pitwall-lab.streamlit.app/~/+/app/static/pitwall-media/method-9776d0597fe6-1200.webp']){
  try{const r=await p.request.get(target,{timeout:15000}),bytes=await r.body();result.events.push({type:'direct_get',url:target,status:r.status(),content_type:r.headers()['content-type'],bytes:bytes.length,sha256:crypto.createHash('sha256').update(bytes).digest('hex')});}
  catch(e){result.events.push({type:'direct_get_error',url:target,error:e.message.split('\n')[0]});}
 }
 await p.screenshot({path:path.join(out,'observed.png')});await c.close();result.status='observed';
}catch(e){result.status='failed';result.error=e.message;}finally{result.utc=new Date().toISOString();fs.writeFileSync(path.join(out,'diagnostic.json'),JSON.stringify(result,null,2));await browser.close();}console.log(JSON.stringify({status:result.status,image:result.image,events:result.events,console:result.console}));})();
