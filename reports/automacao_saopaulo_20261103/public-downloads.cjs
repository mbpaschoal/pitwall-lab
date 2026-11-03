/* PT/EN: live driver coverage, official positions, original JPEG and real exports. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {chromium,devices}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const [baseArg,output]=process.argv.slice(2),base=(baseArg||'').replace(/\/+$/,'');
if(!base||!output)throw Error('Usage: aceite_pilotos_atualizacao.cjs URL OUTPUT');
const root=process.env.PITWALL_SOURCE_ROOT||path.join(__dirname,'../..');
const version=fs.readFileSync(path.join(root,'VERSION'),'utf8').trim();
const baseline=JSON.parse(fs.readFileSync(path.join(root,'frontend_assets/pilotos_condicoes.json')));
const supplement=JSON.parse(fs.readFileSync(path.join(root,'frontend_assets/pilotos_condicoes_operacao.json')));
const rows=baseline.resultados.concat(...Object.values(supplement.events).map(x=>x.results));
const gps={...baseline.gps,...Object.fromEntries(Object.entries(supplement.events).map(([id,x])=>[id,x.gp]))};
const latest=Object.values(gps).sort((a,b)=>a.date_utc.localeCompare(b.date_utc)).at(-1);
const cutoff=latest.date_utc.split('-').reverse().join('/');
const maxStarts=rows.filter(x=>x.driver_id==='max_verstappen'&&x.started).length;
const left=new Map(rows.filter(x=>x.started&&x.driver_id==='max_verstappen'&&gps[x.race_id].temporada===2026).map(x=>[x.race_id,x]));
const common=rows.filter(x=>x.started&&x.driver_id==='alonso'&&gps[x.race_id].temporada===2026&&left.has(x.race_id));
const comparable=common.filter(x=>x.position!==null&&!x.disqualified&&left.get(x.race_id).position!==null&&!left.get(x.race_id).disqualified).length;
const source=JSON.parse(fs.readFileSync(path.join(root,'dashboard_assets/fan/sources.json'))).find(x=>x.driver_id==='ryo_hirakawa');
const check=(ok,msg)=>{if(!ok)throw Error(msg);};fs.mkdirSync(output,{recursive:true});
// BackMsg protobuf field 11 is rerun_script. Ignore heartbeat/ack traffic.
function requestsRerun(payload){
 const b=Buffer.isBuffer(payload)?payload:Buffer.from(payload);let i=0;
 function uint(){let n=0,s=0,v;do{if(i>=b.length||s>49)throw Error('Invalid BackMsg');v=b[i++];n+=(v&127)*2**s;s+=7;}while(v&128);return n;}
 while(i<b.length){const tag=uint(),field=Math.floor(tag/8),wire=tag%8;if(field===11)return true;
  if(wire===0)uint();else if(wire===1)i+=8;else if(wire===2){const len=uint();i+=len;}else if(wire===5)i+=4;else return false;
 }return false;
}

(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHANNEL?{channel:process.env.PLAYWRIGHT_CHANNEL}:{})}),cases=[];
 try{for(const mobile of (process.env.PITWALL_MOBILE_ONLY==='1'?[true]:process.env.PITWALL_DESKTOP_ONLY==='1'?[false]:[false,true]))for(const lang of (process.env.PITWALL_LANG_ONLY?[process.env.PITWALL_LANG_ONLY]:['pt','en'])){
  const responsive=mobile&&process.env.PITWALL_RESPONSIVE_BOOTSTRAP==='1';
  const context=await browser.newContext(responsive?{viewport:{width:1440,height:1100},hasTouch:true}:mobile?{...devices['Pixel 7'],viewport:{width:390,height:844}}:{viewport:{width:1440,height:1100}});
  const network=[];context.on('requestfailed',req=>network.push({path:new URL(req.url()).pathname,failure:req.failure()?.errorText}));context.on('response',r=>{const u=new URL(r.url());if(u.pathname.includes('/media/')&&!u.pathname.includes('/static/'))network.push({type:'media',path:u.pathname,status:r.status(),disposition:r.headers()['content-disposition']});});
  let page=await context.newPage();const key=(mobile?'mobile':'desktop')+'-'+lang;let reloads=0,opened=false,reruns=0;
  page.on('websocket',ws=>{if(ws.url().includes('_stcore/stream'))ws.on('framesent',event=>{if(requestsRerun(event.payload))reruns++;});});
  try{
   async function open(params){
    if(responsive)await page.setViewportSize({width:1440,height:1100});
    const warm=process.env.PITWALL_WARM_PT==='1'&&lang==='en'&&!opened;opened=true;
    await page.goto(base+'/?'+new URLSearchParams({tela:'Pilotos',temporada:'2026',gp:'19',lang:warm?'pt':lang,...params}),{waitUntil:'domcontentloaded',timeout:60000});
    for(let attempt=0;attempt<2;attempt++){
     const app=base.startsWith('http://127.')?page:page.frameLocator('iframe[src*="/~/+/"]').first();
     try{
      await app.getByText('v'+version,{exact:true}).first().waitFor({timeout:60000});
      await app.locator('.fan-hero h1').waitFor({timeout:60000});
      await app.locator('.stApp[data-test-script-state="notRunning"]').waitFor({timeout:60000});
      check(await app.locator('[data-testid="stException"]').count()===0,'App exception');
      if(warm){
       const flag=app.getByRole('button',{name:'🇬🇧 English',exact:true});
       if(mobile)await flag.tap();else await flag.click();
       await app.locator('html[lang="en"]').waitFor({state:'attached',timeout:60000});
       await app.locator('.stApp[data-test-script-state="notRunning"]').waitFor({timeout:60000});
      }
      if(responsive){await page.setViewportSize({width:390,height:844});await page.waitForTimeout(700);}
      return app;
     }catch(error){if(attempt)throw error;reloads++;await page.reload({waitUntil:'domcontentloaded',timeout:60000});}
    }
   }
   async function download(button,extension){
    let cancel,timeout;
    const result=new Promise((resolve,reject)=>{
     const seen=new Set();const listener=async d=>{
      if(!d.suggestedFilename().endsWith(extension))return;
      const failure=await d.failure();
      if(failure){network.push({type:'download-canceled',filename:d.suggestedFilename(),failure});return;}
      cancel();resolve(d);
     };
     const watch=p=>{seen.add(p);p.on('download',listener);};
     cancel=()=>{clearTimeout(timeout);context.off('page',watch);for(const p of seen)p.off('download',listener);};
     for(const p of context.pages())watch(p);context.on('page',watch);
     timeout=setTimeout(()=>{cancel();reject(Error('No download event on any context page'));},45000);
    });
    const [file]=await Promise.all([result,mobile?button.tap():button.click()]);return file;
   }
   async function settled(app){
    await page.waitForTimeout(1500);
    await app.locator('.stApp[data-test-script-state="notRunning"]').waitFor({timeout:45000});
    await page.waitForTimeout(500);
   }
   async function readyButton(app,selector){
    for(let attempt=0;attempt<2;attempt++){
     try{
      await app.locator(selector).waitFor({state:'attached',timeout:45000});
      await app.locator(selector).evaluate(e=>e.scrollIntoView({block:'center'}));
      const button=app.locator(selector+' button');await button.waitFor({state:'visible',timeout:45000});return button;
     }catch(error){
      if(attempt)throw error;
      reloads++;await page.screenshot({path:path.join(output,key+'-native-widget-reload.png')});
      console.log(key+' reloading after native-widget load timeout');
      await page.reload({waitUntil:'domcontentloaded',timeout:60000});
      await app.getByText('v'+version,{exact:true}).first().waitFor({timeout:60000});
      await app.locator('.fan-hero h1').waitFor({timeout:60000});
      await app.locator('.stApp[data-test-script-state="notRunning"]').waitFor({timeout:60000});
     }
    }
   }
   let app=await open({visao:'perfil',piloto:'max_verstappen'});
   check((await app.locator('[data-testid="stCaptionContainer"]').allTextContents()).some(x=>x.includes(cutoff)),'Missing Mexico coverage');
   check((await app.locator('[data-testid="stMetricValue"]').first().innerText())===String(maxStarts),'Stale Max starts');
   await settled(app);
   const csvButton=await readyButton(app,'.st-key-csv_max_verstappen');
   const beforeCSV=reruns;
   const csv=await download(csvButton,'.csv');const csvPath=path.join(output,key+'-max.csv');await csv.saveAs(csvPath);
   await settled(app);check(reruns===beforeCSV,'CSV download reran the app');
   const raw=fs.readFileSync(csvPath,'utf8');check(raw.includes('Mexico')&&raw.includes('gp=19'),'Mexico missing from exported evidence');
   await app.getByText(lang==='pt'?'Compartilhar esta análise':'Share this analysis',{exact:true}).click();
   await settled(app);
   const svgButton=await readyButton(app,'.st-key-share_svg');
   const beforeSVG=reruns;
   const svg=await download(svgButton,'.svg');
   const svgPath=path.join(output,key+'-card.svg');await svg.saveAs(svgPath);check(fs.readFileSync(svgPath,'utf8').includes(cutoff),'Stale shared cutoff');
   await settled(app);check(reruns===beforeSVG,'SVG download reran the app');
   check(fs.readFileSync(svgPath,'utf8').includes(lang==='en'?'Starts':'Largadas'),'Wrong SVG language');
   await page.screenshot({path:path.join(output,key+'-max.png')});

   app=await open({visao:'perfil',piloto:'ryo_hirakawa',anos:'2026'});
   check((await app.locator('.fan-hero h1').innerText()).includes('Hirakawa'),'Driver identity replaced');
   const picture=app.locator('.fan-hero-image');await picture.evaluate(img=>img.decode());
   const image=await picture.evaluate(img=>({src:img.currentSrc,width:img.naturalWidth,height:img.naturalHeight}));
   check(image.width===source.width&&image.height===source.height,'Wrong original portrait resolution');
   check(crypto.createHash('sha256').update(Buffer.from(image.src.split(',')[1],'base64')).digest('hex')===source.sha256,'Wrong Hirakawa portrait');
   check(await app.locator('a.fan-art-label[href*="haasf1team.com"]').count()===1,'Incorrect portrait attribution');
   await page.screenshot({path:path.join(output,key+'-hirakawa.png')});
   app=await open({visao:'perfil',piloto:'norris',anos:'2026'});
   await app.locator('.fan-hero-image').evaluate(img=>img.decode());
   check((await app.locator('.fan-hero h1').innerText()).includes('Norris'),'Legacy portrait profile identity changed');
   check((await app.locator('.fan-hero-image').evaluate(img=>img.naturalWidth))>=512,'Legacy portrait missing or undersized');
   await page.screenshot({path:path.join(output,key+'-norris.png')});
   app=await open({visao:'duelo',piloto:'max_verstappen',rival:'alonso',anos:'2026'});
   check(await app.locator('[data-testid="stException"]').count()===0,'Duel exception');
   const denominator=app.locator('[data-testid="stCaptionContainer"]').filter({hasText:new RegExp(common.length+' (largadas em comum|shared starts)','i')}).first();
   await denominator.waitFor({timeout:30000});
   check((await denominator.innerText()).includes(String(comparable)),'Wrong comparable-result denominator');
   const metrics=await app.locator('[data-testid="stMetric"]').allTextContents();
   cases.push({lang,mobile,responsiveDesktopBootstrap:responsive,version,reloads,maxStarts,csv:true,svg:true,download_reruns:0,warmPortugueseBootstrap:process.env.PITWALL_WARM_PT==='1',svg_separate_page:false,english_selected_by_flag:process.env.PITWALL_WARM_PT==='1'&&lang==='en',hirakawa_original_sha256:source.sha256,duel_metrics:metrics,status:'passed'});
   fs.writeFileSync(path.join(output,'acceptance.json'),JSON.stringify({status:'passed',cases},null,2)+'\n');console.log(key+' passed');
  }catch(e){fs.writeFileSync(path.join(output,key+'-failure.json'),JSON.stringify({message:e.message,network},null,2));await page.screenshot({path:path.join(output,key+'-failure.png')});throw e;}finally{await context.close();}
 }}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
