/* Read-only deployment proof: real menu navigation across all six pages. */
const fs=require('node:fs'),path=require('node:path');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const {ready}=require('../../tests/browser/verificar_publicacao.cjs');
const base='https://pitwall-lab.streamlit.app',version='0.8.29';
const screens=['Corridas','Pilotos','Campeonato','Previsões','Desempenho','Metodologia'];
async function bounded(promise,ms){let timer;try{return await Promise.race([promise,new Promise((_,reject)=>timer=setTimeout(()=>reject(Error('Navigation deadline reached')),ms))]);}finally{clearTimeout(timer);}}
(async()=>{
 const out=path.resolve(process.argv[2]);fs.mkdirSync(out,{recursive:true});
 const options={headless:true};if(process.env.PLAYWRIGHT_CHANNEL)options.channel=process.env.PLAYWRIGHT_CHANNEL;
 const browser=await chromium.launch(options),deadline=Date.now()+480000;
 const report={version,base,started_at_utc:new Date().toISOString(),cases:[]};
 const save=()=>{const file=path.join(out,'navigation.json');fs.writeFileSync(file+'.tmp',JSON.stringify(report,null,2));fs.renameSync(file+'.tmp',file);};
 try{
  for(const width of [1440,390])for(const lang of ['pt','en']){
   const context=await browser.newContext({viewport:{width,height:1000},isMobile:width===390,hasTouch:width===390,deviceScaleFactor:2});
   let page=await context.newPage(),previous=false;
   try{
    for(let i=0;i<screens.length;i++){
     const screen=screens[i],row={width,lang,screen,status:'failed'};report.cases.push(row);
     if(Date.now()>=deadline){row.error='Overall navigation deadline reached';save();continue;}
     try{
      await bounded((async()=>{
       let app=page.frameLocator('iframe[src*="/~/+/"]').first();
       const link=app.locator('.journey-navigation-fallback>a[data-screen="'+screen+'"]');
       if(previous){
        row.control=await link.isVisible()?'link':'native';
        await (row.control==='link'?link:app.locator('.st-key-journey-navigation [role=radiogroup]>label').nth(i)).click();
       }else{
        row.control='direct_url';
        await page.goto(base+'/?'+new URLSearchParams({tela:screen,temporada:'2026',gp:'19',lang}),{waitUntil:'domcontentloaded',timeout:30000});
       }
       row.controls=await ready(app,version,lang);
       await page.waitForURL(u=>u.searchParams.get('tela')===screen&&u.searchParams.get('gp')==='19'&&u.searchParams.get('lang')===lang,{timeout:10000});
       const data=await app.locator('body').evaluate(async()=>{
        const u=new URL(location.href),photos=[];
        for(const image of document.querySelectorAll('.fan-hero-image')){
         if(!image.getClientRects().length)continue;
         await image.decode();if(!image.naturalWidth||!image.naturalHeight)throw Error('Undecoded header photograph');
         photos.push({width:image.naturalWidth,height:image.naturalHeight});
        }
        return{query:Object.fromEntries(['tela','temporada','gp','lang'].map(k=>[k,u.searchParams.get(k)])),photos,title:document.querySelector('.fan-hero h1')?.textContent};
       });
       if(data.query.tela!==screen||data.query.gp!=='19'||data.query.temporada!=='2026'||data.query.lang!==lang)throw Error('Frame context differs');
       if(!data.photos.length)throw Error('No decoded header photograph');
       Object.assign(row,data);await page.screenshot({path:path.join(out,`${width}-${lang}-${i}.jpg`),type:'jpeg',quality:75});
      })(),Math.min(60000,deadline-Date.now()));
      row.status='passed';previous=true;
     }catch(error){
      row.error=error.message;previous=false;
      await page.screenshot({path:path.join(out,`${width}-${lang}-${i}-failed.jpg`),type:'jpeg',quality:70,timeout:3000}).catch(()=>{});
      await page.close();page=await context.newPage();
     }finally{save();}
     console.log(JSON.stringify({width,lang,screen,status:row.status,control:row.control}));
    }
   }finally{await context.close();}
  }
 }finally{
  await browser.close();report.completed_at_utc=new Date().toISOString();report.status=report.cases.length===24&&report.cases.every(r=>r.status==='passed')?'passed':'failed';save();
 }
 if(report.status!=='passed')process.exitCode=1;
})().catch(error=>{console.error(error.message);process.exitCode=1;});
