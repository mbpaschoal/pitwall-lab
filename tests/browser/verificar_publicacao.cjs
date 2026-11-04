/* PT/EN: verify served pixels, hashes, build and hydrated controls. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const sha256=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
function integrity(ok,message){if(!ok){const e=Error(message);e.code='integrity';throw e;}}
async function bounded(promise,ms,label){let timer;try{return await Promise.race([promise,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error(label+' timed out')),ms);})]);}finally{clearTimeout(timer);}}

async function verifyImage(page,app,expected){
 const image=app.locator('.fan-hero-image');await image.waitFor({timeout:20000});
 const actual=await image.evaluate(async e=>{
  let timer;try{await Promise.race([e.decode(),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Photo decoding timed out')),20000);})]);}finally{clearTimeout(timer);}
  return{source:e.currentSrc,width:e.naturalWidth,height:e.naturalHeight};
 });
 integrity(actual.width>0&&actual.height>0,'Photo has no decoded pixels');
 let bytes,variant,mime;
 if(actual.source.startsWith('data:image/')){
  integrity(actual.source.includes(';base64,'),'Unexpected photo encoding');bytes=Buffer.from(actual.source.split(',')[1],'base64');
 }else{
  const url=new URL(actual.source),appURL=new URL(await app.locator('body').evaluate(()=>location.href));
  integrity(url.origin===appURL.origin,'Photo origin differs from the served app');
  variant=expected.variants?.find(v=>url.pathname.endsWith('/app/'+v.path));
  integrity(variant,'Photo is outside the approved variants');
  const response=await page.request.get(url.href,{timeout:20000});mime=response.headers()['content-type']||'';
  integrity(response.ok()&&mime.startsWith('image/'),'Photo response is not an image');bytes=await response.body();
 }
 const digest=sha256(bytes);integrity(digest===(variant?variant.sha256:expected.sha256),'Photo bytes differ from the documented source');
 return{decoded:true,width:actual.width,height:actual.height,sha256:digest,delivery:variant?'static_variant':'inline_original',variant:variant?.path,mime};
}

function inspectControls(_element,lang){
 const visible=e=>{if(!e.getClientRects().length)return false;for(let n=e;n;n=n.parentElement){const s=getComputedStyle(n);if(s.visibility==='hidden'||Number(s.opacity)===0)return false;}return true;};
 const screens=['Corridas','Pilotos','Campeonato','Previsões','Desempenho','Metodologia'];
 const native=[...document.querySelectorAll('.st-key-journey-navigation [role=radiogroup] label')].filter(visible);
 const links=[...document.querySelectorAll('.journey-navigation-fallback>a')].filter(visible);
 const validLinks=links.length===6&&links.every((e,i)=>{
  try{const u=new URL(e.href);return e.dataset.screen===screens[i]&&u.origin===location.origin&&u.pathname===location.pathname&&u.searchParams.get('tela')===screens[i]&&u.searchParams.get('lang')===lang;}catch{return false;}
 });
 const flags=[...document.querySelectorAll('[class*=st-key-pw_language_button_] button')].filter(visible);
 const flagLinks=[...document.querySelectorAll('.pw-language-fallback')].filter(visible);
 const validFlags=flagLinks.every(e=>{try{const u=new URL(e.href);return ['pt','en'].includes(e.dataset.language)&&u.origin===location.origin&&u.searchParams.get('lang')===e.dataset.language;}catch{return false;}});
 const codes=flags.map(e=>e.closest('[class*=st-key-pw_language_button_]').className.match(/_(pt|en)(?:\s|$)/)?.[1]).concat(flagLinks.map(e=>e.dataset.language));
 const navigation=native.length===6&&links.length===0?'native':native.length===0&&validLinks?'links':null;
 const languageControl=codes.length===2&&new Set(codes).size===2&&codes.includes('pt')&&codes.includes('en')&&validFlags?(flags.length===2?'native':flags.length?'mixed':'links'):null;
 return{ready:document.documentElement.lang===lang&&document.querySelector('.stApp')?.dataset.testScriptState==='notRunning'&&!!navigation&&!!languageControl&&document.querySelectorAll('.st-key-journey-context-row [data-testid=stSelectbox]').length===2,
  navigation,language_control:languageControl,native_navigation:native.length,visible_navigation_links:links.length,native_flags:flags.length,visible_language_links:flagLinks.length,
  hidden_native_error_elements:[...document.querySelectorAll('.st-key-tela [data-testid=stAlertContentError],[class*=st-key-pw_language_button_] [data-testid=stAlertContentError]')].filter(e=>!visible(e)).length};
}

async function ready(app,version,lang){
 await app.getByText('v'+version,{exact:true}).first().waitFor({timeout:45000});
 await app.locator('.fan-hero h1').waitFor({timeout:20000});
 const deadline=Date.now()+30000;let state;
 while(Date.now()<deadline){state=await app.locator('body').evaluate(inspectControls,lang);if(state.ready)break;await new Promise(r=>setTimeout(r,200));}
 if(!state?.ready)throw Error('Language or usable controls did not finish loading');
 await app.locator('body').evaluate(async()=>{
  for(const icon of document.querySelectorAll('[data-testid=stIconMaterial]')){
   if(!icon.getClientRects().length)continue;
   const c=getComputedStyle(icon),faces=await document.fonts.load(c.fontSize+' '+c.fontFamily,icon.textContent);
   if(!faces.length)throw Error('Native icon font unavailable');
  }
  await document.fonts.ready;
  await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
 });
 integrity(await app.locator('[data-testid=stException]').count()===0,'Public application exception');
 integrity(await app.locator('[data-testid=stAlertContentError]:visible').count()===0,'Unrecovered visible widget error');
 integrity(!await app.locator('body').evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),'Horizontal overflow');
 return state;
}

function expectations(root,version,identity){
 integrity(/^\d+\.\d+\.\d+$/.test(version||''),'Expected semantic version');
 integrity(Array.isArray(identity)&&identity.length===3&&identity[0]===2026&&Number.isInteger(identity[1])&&identity[1]>0&&typeof identity[2]==='string','Invalid publication event');
 const read=name=>JSON.parse(fs.readFileSync(path.join(root,name),'utf8'));
 const manifest=read('MANIFESTO.json');integrity(manifest.versao_produto===version,'Expected package version differs');
 const calendar=read('frontend_assets/race_weekend.json').dados_2026.corridas;
 integrity(calendar.filter(r=>r.temporada===identity[0]&&r.rodada===identity[1]&&r.circuito_id===identity[2]).length===1,'Publication event differs from the package calendar');
 const state=read('frontend_assets/operacao_fim_semana.json');
 integrity([state,...(state.arquivo_eventos||[])].filter(r=>r.temporada===identity[0]&&r.rodada===identity[1]&&r.circuito_id===identity[2]).length===1,'Publication event has no matching collected state');
 const race=read('dashboard_assets/circuit/catalogo_visual.json').circuitos[identity[2]];
 integrity(race?.foto?.sha256,'Published circuit photograph is absent');
 const method=read('static/pitwall-media/catalog.json').method;
 return{build:manifest.apresentacao_build_sha256,race:{sha256:race.foto.sha256},method:{sha256:method.source_sha256,variants:method.variants}};
}

async function verifyDeployment(version,resultPath,output){
 const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
 const root=path.resolve(process.env.PITWALL_SOURCE_ROOT||path.join(__dirname,'../../distribuicao/pitwall-dashboard'));
 const identity=JSON.parse(fs.readFileSync(resultPath,'utf8')).identidade;
 const base=process.env.PITWALL_PUBLIC_BASE_URL||'https://pitwall-lab.streamlit.app',baseURL=new URL(base);
 const report={schema:'pitwall-publication-acceptance-v2',version,identity,base,verifier_sha256:sha256(fs.readFileSync(__filename)),cases:[]};
 output=path.resolve(output||path.join(path.dirname(resultPath),'public-deployment'));fs.mkdirSync(output,{recursive:true});
 const save=()=>{const temporary=path.join(output,'publication.json.tmp');fs.writeFileSync(temporary,JSON.stringify(report,null,2));fs.renameSync(temporary,path.join(output,'publication.json'));};
 let expected;
 try{integrity(baseURL.protocol==='https:'||['127.0.0.1','localhost'].includes(baseURL.hostname),'Public check requires HTTPS or localhost');expected=expectations(root,version,identity);report.expected_build=expected.build;}
 catch(error){report.status='failed';report.stage='preflight';report.error=error.message;save();throw error;}
 const launch={headless:true};if(process.env.PLAYWRIGHT_CHANNEL)launch.channel=process.env.PLAYWRIGHT_CHANNEL;
 const browser=await chromium.launch(launch),deadline=Date.now()+480000;
 try{
  for(const width of [1440,390])for(const lang of ['pt','en']){
   const row={width,lang,attempts:[],status:'failed'};report.cases.push(row);
   for(let attempt=0;attempt<2&&Date.now()<deadline;attempt++){
    const context=await browser.newContext({viewport:{width,height:1000},isMobile:width===390,hasTouch:width===390,deviceScaleFactor:2});
    const page=await context.newPage(),receipt={attempt,utc:new Date().toISOString()},network=[];
    page.on('requestfailed',r=>{if(/\.(js|css|webp)(\?|$)/.test(r.url()))network.push({path:new URL(r.url()).pathname,error:r.failure()?.errorText});});
    try{
     await bounded((async()=>{
      let previousApp;
      for(const route of ['Corridas','Metodologia']){
       const query=new URLSearchParams({tela:route,temporada:String(identity[0]),gp:String(identity[1]),lang});
       if(route==='Metodologia'&&receipt.Corridas?.controls.navigation==='links')await previousApp.locator('.journey-navigation-fallback>a[data-screen="Metodologia"]').click();
       else await page.goto(base+'/?'+query,{waitUntil:'domcontentloaded',timeout:45000});
       const app=['127.0.0.1','localhost'].includes(baseURL.hostname)?page:page.frameLocator('iframe[src*="/~/+/"]').first();
       const controls=await ready(app,version,lang);previousApp=app;
       await page.waitForURL(u=>u.searchParams.get('tela')===route&&u.searchParams.get('gp')===String(identity[1])&&u.searchParams.get('lang')===lang,{timeout:15000});
       integrity(await app.locator('body').evaluate((_element,{route,round})=>new URL(location.href).searchParams.get('tela')===route&&new URL(location.href).searchParams.get('gp')===String(round),{route,round:identity[1]}),'Served route or GP differs');
       receipt[route]=await verifyImage(page,app,route==='Corridas'?expected.race:expected.method);
       receipt[route].controls=controls;
       if(route==='Corridas')await app.getByText(lang==='pt'?'Acompanhar chegada dos dados':'Track incoming data',{exact:true}).waitFor({timeout:15000});
       else{
        const details=app.locator('[data-testid=stExpander] summary').filter({hasText:lang==='pt'?'Para quem quer ir além':'For a closer look'});
        await details.click();await app.getByText(expected.build,{exact:false}).first().waitFor({timeout:15000});receipt.observed_build=expected.build;await details.click();
        await app.locator('.fan-hero h1').scrollIntoViewIfNeeded();
       }
       await page.screenshot({path:path.join(output,`${width}-${lang}-${attempt}-${route}.jpg`),type:'jpeg',quality:80});
      }
      const other=lang==='pt'?'en':'pt',link=previousApp.locator('.pw-language-fallback[data-language="'+other+'"]');
      const usedLink=await link.isVisible();
      await (usedLink?link:previousApp.getByRole('button',{name:other==='pt'?/🇧🇷/:/🇬🇧/})).click();
      const switched=await ready(previousApp,version,other);
      await page.waitForURL(u=>u.searchParams.get('tela')==='Metodologia'&&u.searchParams.get('gp')===String(identity[1])&&u.searchParams.get('lang')===other,{timeout:15000});
      integrity(await previousApp.locator('body').evaluate((_element,{other,round})=>{const u=new URL(location.href);return u.searchParams.get('lang')===other&&u.searchParams.get('gp')===String(round)&&u.searchParams.get('tela')==='Metodologia';},{other,round:identity[1]}),'Language switch lost event or route');
      await previousApp.locator('.fan-hero h1').filter({hasText:other==='en'?'How it works':'Como funciona'}).waitFor({timeout:15000});
      receipt.language_transition={from:lang,to:other,control:usedLink?'link':'native',controls:switched};
     })(),Math.min(120000,deadline-Date.now()),'Public acceptance');
     receipt.status='passed';row.status='passed';break;
    }catch(error){receipt.status='failed';receipt.error=error.message;receipt.category=error.code==='integrity'?'integrity':'loading';
     await page.screenshot({path:path.join(output,`${width}-${lang}-${attempt}-failed.jpg`),type:'jpeg',quality:80,timeout:5000}).catch(()=>{});
     if(error.code==='integrity')break;
    }finally{receipt.network_failures=network;row.attempts.push(receipt);save();await context.close();}
   }
   if(!row.attempts.length)row.reason='acceptance_deadline_reached';
   save();console.log(JSON.stringify({width,lang,status:row.status,attempts:row.attempts.length}));
  }
 }finally{await browser.close();report.utc=new Date().toISOString();report.status=report.cases.length===4&&report.cases.every(r=>r.status==='passed')?'passed':'failed';save();}
 integrity(report.status==='passed','Public deployment acceptance failed; retained publication.json contains all attempts');return report;
}

module.exports={verifyImage,expectations,verifyDeployment,ready,inspectControls};
if(require.main===module)verifyDeployment(...process.argv.slice(2)).catch(error=>{console.error(error.message);process.exitCode=1;});
