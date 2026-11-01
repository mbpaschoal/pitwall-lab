/* PT/EN: Composition C geometry, readability and real image checks. */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const [base, output] = process.argv.slice(2);
if (!base || !output) throw Error('Usage: node aceite_visual.cjs URL OUTPUT');
const version = fs.readFileSync(path.join(__dirname,'../../VERSION'),'utf8').trim();
const expectedCSS=fs.readFileSync(path.join(__dirname,'../../frontend_assets/journey.css'),'utf8');
const cssHash=crypto.createHash('sha256').update(expectedCSS).digest('hex');
const heroCatalog=JSON.parse(fs.readFileSync(path.join(__dirname,'../../dashboard_assets/fan/hero_catalog.json'),'utf8')).heroes;
const circuitCatalog=JSON.parse(fs.readFileSync(path.join(__dirname,'../../dashboard_assets/circuit/catalogo_visual.json'),'utf8')).circuitos;
const expectedHeroes={Corridas:circuitCatalog.americas.foto.sha256,Pilotos:heroCatalog.drivers.sha256,Campeonato:heroCatalog.championship.sha256,'Previsões':heroCatalog.forecast.sha256,Desempenho:heroCatalog.performance.sha256,Metodologia:heroCatalog.method.sha256};
const routes = ['Corridas','Pilotos','Campeonato','Previsões','Desempenho','Metodologia'];
const launch = {headless:true};
if (process.env.PLAYWRIGHT_CHANNEL) launch.channel=process.env.PLAYWRIGHT_CHANNEL;
fs.mkdirSync(output,{recursive:true});
const requireCheck=(condition,message)=>{if(!condition)throw Error(message);};

(async()=>{
 const browser=await chromium.launch(launch);
 const evidence=[];
 try {
  for(const mobile of [false,true]) for(const lang of ['pt','en']) for(const route of routes){
   // C's lower three panels have a shallower aspect ratio than the top row.
   const viewport=mobile?{width:390,height:844}:{width:1040,height:routes.indexOf(route)<3?992:875};
   const context=await browser.newContext({viewport,isMobile:mobile,hasTouch:mobile,deviceScaleFactor:2});
   const page=await context.newPage();
   const errors=[];page.on('pageerror',error=>errors.push(error.message));
   const key=`${mobile?'mobile':'desktop'}-${lang}-${route}`;
   try {
    const query=new URLSearchParams({tela:route,temporada:'2026',gp:'18',lang});
    await page.goto(`${base}/?${query}`);
    let surface=page;
    if(!/^https?:\/\/(127\.0\.0\.1|localhost)(:|\/)/.test(base)){
     await page.waitForFunction(()=>Array.from(document.querySelectorAll('iframe')).some(f=>f.src.includes('/~/+/')),null,{timeout:60000});
     for(let i=0;i<15&&!page.frames().some(f=>f.url().includes('/~/+/'));i++)await page.waitForTimeout(1000);
     surface=page.frames().find(f=>f.url().includes('/~/+/'));
     requireCheck(surface,'Streamlit app frame unavailable');
    }
    await surface.locator('.fan-hero h1').waitFor({timeout:90000});
    await surface.waitForFunction(()=>document.querySelector('.stApp')?.getAttribute('data-test-script-state')==='notRunning',null,{timeout:90000});
    await surface.locator('.fan-hero-image').evaluate(img=>img.decode());
    const photoSource=await surface.locator('.fan-hero-image').getAttribute('src');
    const photoHash=crypto.createHash('sha256').update(Buffer.from(photoSource.split(',')[1],'base64')).digest('hex');
    requireCheck(photoHash===expectedHeroes[route],'Served photograph differs from the original source');
    await surface.evaluate(()=>document.fonts.ready);
    await page.waitForTimeout(700);
    requireCheck(await surface.locator('[data-testid="stException"]').count()===0,'Application exception');
    requireCheck(errors.length===0,errors.join('; '));
    requireCheck((await surface.locator('body').innerText()).includes('v'+version),'Wrong served version');
    requireCheck((await surface.locator('style').allTextContents()).some(style=>style.includes(expectedCSS)),'Served composition CSS differs from the release');
    const measurements=await surface.evaluate(({route,mobile})=>{
     const box=element=>{if(!element)return null;const r=element.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,bottom:r.bottom,right:r.right};};
     const one=selector=>box(document.querySelector(selector));
     const photos=Array.from(document.querySelectorAll('.fan-hero-image,.fan-hero-backdrop,.fan-portrait')).filter(i=>i.getBoundingClientRect().width>0).map(i=>({driver:i.dataset.driverId,natural:[i.naturalWidth,i.naturalHeight],display:[i.getBoundingClientRect().width,i.getBoundingClientRect().height]}));
     return {viewport:[innerWidth,innerHeight],overflow:document.documentElement.scrollWidth>innerWidth,
      hero:one('.fan-hero'),heading:one('.fan-hero h1'),copy:one('.fan-hero-copy>p'),ribbon:one('.journey-calendar'),
      dock:one('.st-key-journey-navigation'),targets:Array.from(document.querySelectorAll('.st-key-journey-navigation [role="radiogroup"]>label')).map(box),photos,
      podium:one('.fan-podium-panel'),podiumHeading:one('.fan-podium-panel h2'),weather:one('.fan-weather'),details:one('.fan-circuit-more'),
      chips:one('.fan-condition-chips'),scope:one('.fan-pilot-toolbar'),
      championshipRows:document.querySelectorAll('.tabela-editorial tbody tr').length,
      probabilities:one('.fan-probability-list'),after:one('.st-key-prediction-after'),compact:one('.fan-podium-compact'),
      results:one('.fan-results'),resultsHeader:one('.fan-results-header'),legend:one('.fan-results-legend'),
      steps:Array.from(document.querySelectorAll('.fan-process-step')).map(box),
      stepFont:document.querySelector('.fan-process-step p')?parseFloat(getComputedStyle(document.querySelector('.fan-process-step p')).fontSize):null,
      documents:Array.from(document.querySelectorAll('.fan-document-links>a')).map(box),
      h1Count:document.querySelectorAll('h1').length,
      bars:Array.from(document.querySelectorAll('.fan-condition-bar>i,.fan-probability-track>i')).map(i=>parseFloat(i.style.width))};
    },{route,mobile});
    const m=measurements, width=m.viewport[0];
    fs.writeFileSync(path.join(output,key+'-geometry.json'),JSON.stringify(m,null,2));
    requireCheck(!m.overflow,'Horizontal overflow');
    requireCheck(m.h1Count===1,'One main title required');
    requireCheck(m.hero.y>=m.ribbon.bottom-1 && m.hero.y<m.ribbon.bottom+(route==='Pilotos'&&mobile?80:24),'Cover detached from the GP ribbon');
    requireCheck(m.heading.y>=m.hero.y&&m.heading.bottom<=m.hero.bottom,'Title clipped by cover');
    requireCheck(m.targets.length===6&&m.targets.every(r=>r.width>=44&&r.height>=44&&r.x>=0&&r.right<=width+1),'Dock target clipped or too small');
    requireCheck(m.dock.bottom<=m.viewport[1]-54,'Dock overlaps the Streamlit host area');
    requireCheck(m.photos.every(i=>i.natural[0]>=i.display[0]*2 && i.natural[1]>=i.display[1]*2),'Photograph lacks source resolution for 2x display');
    requireCheck(m.bars.every(value=>value>=0&&value<=100),'Chart exceeds its container');
    if(route==='Corridas'){
     requireCheck(m.podiumHeading.y>=m.hero.y+m.hero.height*.8,'Podium displaced above the photograph');
     requireCheck(m.weather.bottom<=m.details.y+1,'Circuit details interrupt weather');
     requireCheck((await surface.locator('.fan-podium-place').evaluateAll(items=>items.map(i=>i.className.match(/fan-place-(\d)/)[1]))).join(',')==='2,1,3','Observed podium order changed');
    }
    if(route==='Pilotos'){
     requireCheck(m.scope.bottom<=m.heading.y-4,'Driver criteria overlap title');
     requireCheck(m.copy.bottom<=m.chips.y-4,'Driver copy overlaps filters');
    }
    if(route==='Campeonato'){
     requireCheck(m.championshipRows>25,'Championship truncated');
     requireCheck(m.hero.height<=(mobile?210:200),'Championship cover displaces the standings');
    }
    if(route==='Previsões'){
     requireCheck(m.compact&&m.after,'Missing observed comparison');
     requireCheck(!m.podiumHeading,'Duplicate podium heading in forecast');
     requireCheck(m.probabilities.y>=m.copy.bottom,'Forecast rows overlap introduction');
     requireCheck(m.after.y>=m.probabilities.bottom,'Before/after stages overlap');
     if(!mobile)requireCheck(m.after.bottom<=m.dock.y-8,'Observed podium hidden behind navigation');
    }
    if(route==='Desempenho'){
     requireCheck(m.resultsHeader&&m.legend,'Missing results legend');
     if(!mobile)requireCheck(m.legend.x>m.resultsHeader.x+m.resultsHeader.width*.5,'Legend displaces comparison heading');
     requireCheck(await surface.locator('.fan-gp-result[data-evaluated="true"]').count()===1,'Unvalidated races counted as evaluations');
    }
    if(route==='Metodologia'){
     requireCheck(m.steps.length===3&&m.documents.length===2,'Method explanation incomplete');
     requireCheck(m.steps.every((r,i)=>i===0||r.y>=m.steps[i-1].bottom),'Method cards overlap');
     requireCheck(m.documents[0].y>=m.steps[2].bottom,'Document links overlap steps');
     if(!mobile)requireCheck(m.documents.every(r=>r.bottom<=m.dock.y-8),'Method documents hidden behind navigation');
     if(mobile)requireCheck(m.stepFont>=13,'Mobile explanation too small');
    }
    await page.screenshot({path:path.join(output,key+'.png')});
    evidence.push({route,lang,mobile,status:'passed',photo_sha256:photoHash,measurements:m});
    fs.writeFileSync(path.join(output,'acceptance.json'),JSON.stringify({version,css_sha256:cssHash,cases:evidence},null,2));
    console.log(key+' passed');
   }catch(error){await page.screenshot({path:path.join(output,key+'-failure.png')});throw Error(key+': '+error.message);}
   finally{await context.close();}
  }
 }finally{await browser.close();}
 console.log(JSON.stringify({status:'passed',version,cases:evidence.length}));
})().catch(error=>{console.error(error);process.exit(1);});
