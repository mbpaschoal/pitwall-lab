/* Read-only diagnostic; compare public wrapper, existing iframe and documented embed. */
const fs=require('node:fs'),path=require('node:path');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const origin='https://pitwall-lab.streamlit.app';
const query=new URLSearchParams({tela:'Metodologia',temporada:'2026',gp:'19',lang:'pt'});
const safeURL=raw=>{try{const u=new URL(raw);return u.origin+u.pathname;}catch{return '[invalid URL]';}};
const safeError=error=>String(error.message||error).split('\nCall log:')[0].slice(0,400);
(async()=>{
 const out=path.resolve(process.argv[2]);fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHANNEL?{channel:process.env.PLAYWRIGHT_CHANNEL}:{})});
 const report={started_at_utc:new Date().toISOString(),expected_version:'0.8.29',diagnostic_only:true,cases:[]};
 const save=()=>{fs.writeFileSync(path.join(out,'hosting.json.tmp'),JSON.stringify(report,null,2));fs.renameSync(path.join(out,'hosting.json.tmp'),path.join(out,'hosting.json'));};
 let iframeURL;
 try{
  for(const mode of ['public_wrapper','existing_iframe_direct','documented_embed']){
   const row={mode,requests:[],websockets:[],samples:[]};report.cases.push(row);
   if(mode==='existing_iframe_direct'&&!iframeURL){row.status='not_run';row.reason='No existing app iframe was observed';save();continue;}
   const context=await browser.newContext({viewport:{width:390,height:900},isMobile:true,hasTouch:true});
   const page=await context.newPage();
   page.on('response',response=>{const u=new URL(response.url());if(u.hostname==='pitwall-lab.streamlit.app'&&(response.status()>=400||['document','script','font','stylesheet'].includes(response.request().resourceType())))row.requests.push({url:safeURL(u),status:response.status(),type:response.request().resourceType(),mime:response.headers()['content-type']});});
   page.on('requestfailed',request=>row.requests.push({url:safeURL(request.url()),type:request.resourceType(),error:request.failure()?.errorText}));
   page.on('websocket',socket=>{const item={url:safeURL(socket.url()),received:0,sent:0,closed:false};row.websockets.push(item);socket.on('framereceived',()=>item.received++);socket.on('framesent',()=>item.sent++);socket.on('close',()=>item.closed=true);});
   try{
    let target=origin+'/?'+query;
    if(mode==='existing_iframe_direct'){target=new URL(iframeURL);target.search=query.toString();target=target.href;}
    if(mode==='documented_embed')target+='&embed=true';
    await page.goto(target,{waitUntil:'domcontentloaded',timeout:30000});
    for(let n=0;n<8;n++){
     await new Promise(resolve=>setTimeout(resolve,5000));
     const frame=page.frames().find(f=>f.url().includes('/~/+/'));
     if(frame&&!iframeURL)iframeURL=frame.url();
     const app=frame||(mode!=='public_wrapper'?page.mainFrame():null);
     const sample={utc:new Date().toISOString(),iframe:!!frame};
     if(app)Object.assign(sample,await app.locator('body').evaluate(()=>({
      lang:document.documentElement.lang,state:document.querySelector('.stApp')?.dataset.testScriptState,
      version:[...document.querySelectorAll('body *')].some(e=>e.childElementCount===0&&e.textContent==='v0.8.29'),
      title:document.querySelector('.fan-hero h1')?.textContent,
      native_menu:document.querySelectorAll('.st-key-journey-navigation [role=radiogroup]>label').length,
      link_menu:document.querySelectorAll('.journey-navigation-fallback>a').length,
      selectors:document.querySelectorAll('.st-key-journey-context-row [data-baseweb=select]').length,
      photos:[...document.querySelectorAll('.fan-hero-image')].map(e=>({complete:e.complete,width:e.naturalWidth,height:e.naturalHeight})),
      exceptions:document.querySelectorAll('[data-testid=stException]').length
     })).catch(()=>({document_unavailable:true})));
     row.samples.push(sample);save();
     if(sample.version&&sample.title&&sample.state==='notRunning'&&sample.selectors===2&&sample.photos?.every(p=>p.width>0))break;
    }
    row.status=row.samples.some(s=>s.version&&s.title&&s.state==='notRunning'&&s.selectors===2&&s.photos?.every(p=>p.width>0))?'page_observed':'loading_incomplete';
    await page.screenshot({path:path.join(out,mode+'.jpg'),type:'jpeg',quality:70});
   }catch(error){row.status='failed';row.error=safeError(error);}
   finally{save();await context.close();}
  }
 }finally{await browser.close();report.completed_at_utc=new Date().toISOString();save();}
 console.log(JSON.stringify(report.cases.map(({mode,status,error})=>({mode,status,error}))));
})().catch(error=>{console.error(safeError(error));process.exitCode=1;});
