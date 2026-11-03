const fs=require('node:fs'),path=require('node:path');
const {chromium,devices}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const out=process.argv[2];fs.mkdirSync(out,{recursive:true});
function requestsRerun(payload){
 const b=Buffer.isBuffer(payload)?payload:Buffer.from(payload);let i=0;
 function uint(){let n=0,s=0,v;do{if(i>=b.length||s>49)throw Error('Invalid BackMsg');v=b[i++];n+=(v&127)*2**s;s+=7;}while(v&128);return n;}
 while(i<b.length){const tag=uint(),field=Math.floor(tag/8),wire=tag%8;if(field===11)return true;
  if(wire===0)uint();else if(wire===1)i+=8;else if(wire===2){const len=uint();i+=len;}else if(wire===5)i+=4;else return false;
 }return false;
}

(async()=>{const browser=await chromium.launch({headless:true,channel:'chrome'});try{
 for(const mobile of (process.env.PITWALL_DEVICE_FILTER==='desktop'?[false]:process.env.PITWALL_DEVICE_FILTER==='mobile'?[true]:[false,true]))for(const lang of (process.env.PITWALL_LANG_ONLY?[process.env.PITWALL_LANG_ONLY]:['pt','en'])){const welcome=false;
 const ctx=await browser.newContext(mobile?{...devices['Pixel 7'],viewport:{width:390,height:844},acceptDownloads:true}:{viewport:{width:1440,height:1100},acceptDownloads:true});const page=await ctx.newPage();const key=(mobile?'mobile':'desktop')+'-'+lang;let reruns=0,reloads=0;const network=[];
 page.on('websocket',ws=>{if(ws.url().includes('_stcore/stream'))ws.on('framesent',e=>{if(requestsRerun(e.payload))reruns++;});});
 page.on('requestfailed',r=>network.push({path:new URL(r.url()).pathname,error:r.failure()?.errorText}));
 const app=page.frameLocator('iframe[src*="/~/+/"]').first();
 async function ready(url){await page.goto(url,{waitUntil:'domcontentloaded',timeout:60000});for(let i=0;i<2;i++){try{await app.getByText('v0.8.26',{exact:true}).first().waitFor({timeout:60000});await app.locator('.fan-hero h1').waitFor({timeout:60000});await app.locator('.stApp[data-test-script-state="notRunning"]').waitFor({timeout:60000});return;}catch(e){if(i)throw e;reloads++;await page.reload({waitUntil:'domcontentloaded'});}}}
 async function save(button,extension){let finish,timer;const watchers=[];const promise=new Promise((resolve,reject)=>{const listen=p=>{const fn=async d=>{if(!d.suggestedFilename().endsWith(extension))return;const err=await d.failure();if(err)return;finish();resolve(d);};p.on('download',fn);watchers.push([p,fn]);};for(const p of ctx.pages())listen(p);ctx.on('page',listen);finish=()=>{clearTimeout(timer);ctx.off('page',listen);for(const [p,fn] of watchers)p.off('download',fn);};timer=setTimeout(()=>{finish();reject(Error('Download did not complete'));},45000);});const [d]=await Promise.all([promise,mobile?button.tap():button.click()]);await d.saveAs(path.join(out,key+extension));}
 try{
 if(welcome)await ready('https://pitwall-lab.streamlit.app/?tela=Metodologia&temporada=2026&gp=19&lang=en');
 const params={tela:'Pilotos',visao:'perfil',anos:'2024,2025,2026',metrica:'win_rate',minimo:'5',lang,condicao:'rain',faixas:'rain,track_hot,ccw,many_corners,high_altitude,track_cold',temporada:'2026',gp:'19',piloto:'max_verstappen'};
 await ready('https://pitwall-lab.streamlit.app/?'+new URLSearchParams(params));
 for(const [wrapper,ext] of [['.st-key-share_svg','.svg'],['.st-key-csv_max_verstappen','.csv']]){
 if(ext==='.svg')await app.getByText(lang==='en'?'Share this analysis':'Compartilhar esta análise',{exact:true}).click();
 await app.locator(wrapper).waitFor({state:'attached',timeout:45000});await app.locator(wrapper).evaluate(e=>e.scrollIntoView({block:'center'}));const button=app.locator(wrapper+' button');await button.waitFor({state:'visible',timeout:45000});await page.waitForTimeout(1000);const before=reruns;await save(button,ext);await page.waitForTimeout(1000);if(before!==reruns)throw Error('Download reran the app');
 if(ext==='.svg'&&!fs.readFileSync(path.join(out,key+ext),'utf8').includes(lang==='en'?'Starts':'Largadas'))throw Error('Wrong SVG language');
 }
 await page.screenshot({path:path.join(out,key+'-passed.png')});fs.writeFileSync(path.join(out,key+'.json'),JSON.stringify({status:'passed',version:'0.8.26',lang,device:mobile?'Pixel 7':'desktop',viewport:mobile?{width:390,height:844}:{width:1440,height:1100},welcomeBootstrap:welcome,canonicalUrl:true,svgFirst:true,reloads,download_reruns:0,utc:new Date().toISOString()},null,2));console.log(key+' passed');
 }catch(e){await page.screenshot({path:path.join(out,key+'-failed.png')});fs.writeFileSync(path.join(out,key+'.json'),JSON.stringify({status:'failed',message:e.message,welcomeBootstrap:welcome,canonicalUrl:true,network,utc:new Date().toISOString()},null,2));console.log(key+' failed: '+e.message.split('\n')[0]);}finally{await ctx.close();}
 }
 }finally{await browser.close();}})().catch(e=>{console.error(e);process.exit(1)});
