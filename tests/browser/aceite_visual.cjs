const {reveal,closeCards}=require('./sidebar_navigation.cjs');
/* PT/EN: Editorial geometry, scroll access, original images and vector covers. */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const engines = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const browserName = process.env.PLAYWRIGHT_BROWSER || 'chromium';
if (!['chromium','webkit'].includes(browserName)) throw Error('Unsupported PLAYWRIGHT_BROWSER');
const [base, output] = process.argv.slice(2);
if (!base || !output) throw Error('Usage: node aceite_visual.cjs URL OUTPUT');
const version = fs.readFileSync(path.join(__dirname,'../../VERSION'),'utf8').trim();
const expectedCSS=fs.readFileSync(path.join(__dirname,'../../frontend_assets/journey.css'),'utf8');
const cssHash=crypto.createHash('sha256').update(expectedCSS).digest('hex');
const heroCatalog=JSON.parse(fs.readFileSync(path.join(__dirname,'../../dashboard_assets/fan/hero_catalog.json'),'utf8')).heroes;
const artCatalog=JSON.parse(fs.readFileSync(path.join(__dirname,'../../frontend_assets/destination_illustrations.json'),'utf8')).circuits;
const mediaCatalog=JSON.parse(fs.readFileSync(path.join(__dirname,'../../static/pitwall-media/catalog.json'),'utf8')).method;
const expectedHeroes={Corridas:artCatalog.americas.sha256,Pilotos:heroCatalog.drivers.sha256,Campeonato:heroCatalog.championship.sha256,'Previsões':artCatalog.americas.sha256,Desempenho:heroCatalog.performance.sha256,Metodologia:heroCatalog.method.sha256};
const routes = ['Corridas','Pilotos','Campeonato','Previsões','Desempenho','Metodologia'];
const launch = {headless:true};
if (browserName==='chromium' && process.env.PLAYWRIGHT_CHANNEL) launch.channel=process.env.PLAYWRIGHT_CHANNEL;
fs.mkdirSync(output,{recursive:true});
const requireCheck=(condition,message)=>{if(!condition)throw Error(message);};

(async()=>{
 const browser=await engines[browserName].launch(launch);
 const evidence=[];
 try {
  for(const mobile of [false,true]) for(const lang of ['pt','en']) for(const route of routes){
   // The menu shares normal flow; the main scrollport stays inside the viewport.
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
    const image=surface.locator(['Corridas','Previsões'].includes(route)?'.pc-illustration':'.fan-hero-image').first();
    await image.evaluate(img=>img.decode());
    const photoSource=await image.evaluate(img=>img.currentSrc);
    let photoBytes,variant;
    if(photoSource.startsWith('data:'))photoBytes=Buffer.from(photoSource.split(',')[1],'base64');
    else {
     variant=mediaCatalog.variants.find(v=>new URL(photoSource).pathname.endsWith('/app/'+v.path));
     const originalPath='/app/'+artCatalog.americas.path;
     const immutable=['Corridas','Previsões'].includes(route)&&new URL(photoSource).pathname.endsWith(originalPath);
     requireCheck(immutable||variant&&mediaCatalog.source_sha256===expectedHeroes[route],'Photo is not the approved immutable original or responsive variant');
     requireCheck(new URL(photoSource).origin===new URL(surface.url()).origin,'Photo origin differs');
     const response=await page.request.get(photoSource);requireCheck(response.ok(),'Responsive image did not load');photoBytes=await response.body();
    }
    const photoHash=crypto.createHash('sha256').update(photoBytes).digest('hex');
    requireCheck(photoHash===(variant?variant.sha256:expectedHeroes[route]),'Served photograph differs from its documented source or variant');
    await surface.evaluate(async()=>{
     await document.fonts.ready;
     // Streamlit can introduce Material Symbols after the first fonts.ready.
     // Load those faces explicitly instead of treating a fallback word as a glyph.
     for(const icon of document.querySelectorAll('[data-testid="stIconMaterial"]')){const c=getComputedStyle(icon);await document.fonts.load(c.fontSize+' '+c.fontFamily,icon.textContent);}
     await document.fonts.ready;
     await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
    });
    await surface.waitForFunction(expected=>document.documentElement.lang===expected,lang,{timeout:15000});
    // Server idle can precede Streamlit's lazy native-widget hydration.
    // Geometry and hit tests require the real controls, not their skeletons.
    await surface.waitForFunction(expected=>{
     const labels=Array.from(document.querySelectorAll('.st-key-pw-sidebar-menu button'));
     const selects=document.querySelectorAll('.st-key-journey-context-row [data-testid="stSelectbox"]');
     return document.querySelector('.stApp')?.dataset.testScriptState==='notRunning'&&document.documentElement.lang===expected&&document.fonts.status==='loaded'&&labels.length===15&&selects.length===2;
    },lang,{timeout:90000});
    await surface.evaluate(async()=>{await document.fonts.ready;await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));});
    await page.waitForTimeout(700);
    for(const img of await surface.locator('.fan-hero-image,.fan-hero-backdrop,.fan-portrait').filter({visible:true}).all()){await img.scrollIntoViewIfNeeded();await img.evaluate(e=>e.decode());}
    await surface.locator('.stMain').evaluate(e=>e.scrollTo({top:0,behavior:'instant'}));
    requireCheck(await surface.locator('[data-testid="stException"]').count()===0,'Application exception');
    requireCheck(errors.length===0,errors.join('; '));
    requireCheck((await surface.locator('body').innerText()).includes('v'+version),'Wrong served version');
    requireCheck((await surface.locator('style').allTextContents()).some(style=>style.includes(expectedCSS)),'Served composition CSS differs from the release');
    const measurements=await surface.evaluate(({route,mobile})=>{
     const box=element=>{if(!element)return null;const r=element.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,bottom:r.bottom,right:r.right};};
     const one=selector=>box(document.querySelector(selector));
     const photos=Array.from(document.querySelectorAll('.fan-hero-image,.fan-hero-backdrop,.fan-portrait')).filter(i=>i.getBoundingClientRect().width>0).map(i=>({driver:i.dataset.driverId,natural:[i.naturalWidth,i.naturalHeight],responsive:i.hasAttribute('srcset'),display:[i.getBoundingClientRect().width,i.getBoundingClientRect().height]}));
     const blocks='.st-key-race-summary,.stTabs:has(.fan-circuit-details),.fan-pilot-ranking,.st-key-fan-prediction-intro,.fan-results,.fan-process,.st-key-pilot-view-navigation,.fan-pilot-toolbar,.fan-condition-chips,.fan-photo-credits';
     return {viewport:[innerWidth,innerHeight],overflow:document.documentElement.scrollWidth>innerWidth,
      main:one('.stMain'),normalBlocks:Array.from(document.querySelectorAll(blocks)).filter(n=>n.getClientRects().length).map(n=>({className:n.className,marginTop:parseFloat(getComputedStyle(n).marginTop),marginBottom:parseFloat(getComputedStyle(n).marginBottom),position:getComputedStyle(n).position})),
      hero:one('.fan-hero'),heading:one('.fan-hero h1'),copy:one('.fan-hero-copy>p'),ribbon:one('.journey-calendar'),
      dock:one('.st-key-journey-navigation'),targets:Array.from(document.querySelectorAll('.st-key-pw-sidebar-menu button')).map(box),photos,
      podium:one('.fan-podium-panel'),podiumHeading:one('.fan-podium-panel h2'),weather:one('.fan-weather'),details:one('.fan-circuit-more'),
      chips:one('.fan-condition-chips'),scope:one('.fan-pilot-toolbar'),pilotNavigation:one('.st-key-pilot-view-navigation'),
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
    // srcset naturalWidth is density-corrected; source pixels come from the
    // byte-verified derivative, rather than treating CSS pixels as source pixels.
    for(const photo of m.photos)if(photo.responsive&&variant)photo.sourcePixels=[variant.width,variant.height];
    fs.writeFileSync(path.join(output,key+'-geometry.json'),JSON.stringify(m,null,2));
    requireCheck(!m.overflow,'Horizontal overflow');
    requireCheck(m.h1Count===1,'One main title required');
    requireCheck(m.main.bottom<=m.viewport[1]+1,'Main scrollport extends beyond viewport');
    requireCheck(m.normalBlocks.every(b=>b.marginTop>=0&&b.marginBottom>=0&&!['absolute','fixed'].includes(b.position)),'Content section leaves normal flow or uses a negative margin');
    const precedingSelector=route==='Previsões'&&await surface.locator('.st-key-open_tarot').count()?'.st-key-open_tarot':'.st-key-journey-context-row';
    const beforeCover=route==='Pilotos'?m.pilotNavigation:await surface.locator(precedingSelector).boundingBox().then(r=>({...r,bottom:r.y+r.height}));
    requireCheck(beforeCover&&m.hero.y>=beforeCover.bottom-1&&m.hero.y<beforeCover.bottom+70,'Cover overlaps or detaches from its preceding navigation');
    requireCheck(m.heading.y>=m.hero.y&&m.heading.bottom<=m.hero.bottom,'Title clipped by cover');
    requireCheck(m.targets.length===15,'Sidebar destinations missing');
    requireCheck(await surface.locator('.st-key-journey-navigation:visible,.journey-calendar:visible').count()===0,'Redundant navigation visible');
    requireCheck(m.photos.every(i=>(i.sourcePixels||i.natural)[0]>=i.display[0]*2 && (i.sourcePixels||i.natural)[1]>=i.display[1]*2),'Photograph lacks source resolution for 2x display');
    requireCheck(m.bars.every(value=>value>=0&&value<=100),'Chart exceeds its container');
    if(route==='Corridas'){
     requireCheck(m.podiumHeading.y>=m.hero.y+m.hero.height*.8,'Podium displaced above the photograph');
     requireCheck(m.weather&&m.details,'Circuit details or weather missing');
     requireCheck((await surface.locator('.fan-podium-place').evaluateAll(items=>items.map(i=>i.className.match(/fan-place-(\d)/)[1]))).join(',')==='2,1,3','Observed podium order changed');
    }
    if(route==='Pilotos'){
     requireCheck(m.scope.y>=m.hero.bottom-1,'Driver metadata overlaps cover');
     requireCheck(m.copy.bottom<=m.chips.y-4,'Driver copy overlaps filters');
    }
    if(route==='Campeonato'){
     requireCheck(m.championshipRows>25,'Championship truncated');
     requireCheck(m.hero.height<=(mobile?210:200),'Championship cover displaces the standings');
    }
    if(route==='Previsões'){
     requireCheck(await surface.locator('.st-key-forecast-details:visible,.fan-probability-row:visible').count()===0,'Forecast revealed before cards');
     requireCheck(await surface.locator('.pw-postcard .pc-scene').isVisible(),'Editorial destination illustration missing');
     await reveal(surface,lang);
     requireCheck(await surface.locator('.pw-tarot-prob').count()===3,'Recorded probabilities missing after reveal');
     requireCheck(m.compact&&m.after,'Missing observed comparison');
     requireCheck(!m.podiumHeading,'Duplicate podium heading in forecast');
     await closeCards(surface);
    }
    if(route==='Desempenho'){
     requireCheck(m.resultsHeader&&m.legend,'Missing results legend');
     if(!mobile)requireCheck(m.legend.x>m.resultsHeader.x+m.resultsHeader.width*.5,'Legend displaces comparison heading');
     requireCheck(await surface.locator('.fan-gp-result[data-evaluated="true"]').count()===2,'Validated Austin and Mexico must be evaluated');
    }
    if(route==='Metodologia'){
     requireCheck(m.steps.length===3&&m.documents.length===2,'Method explanation incomplete');
     requireCheck(m.steps.every((r,i)=>i===0||r.y>=m.steps[i-1].bottom),'Method cards overlap');
     requireCheck(m.documents[0].y>=m.steps[2].bottom,'Document links overlap steps');
     if(mobile)requireCheck(m.stepFont>=13,'Mobile explanation too small');
    }
    // Long screens preserve normal flow. Reach each
    // relevant item by scrolling, then verify that its painted target is usable.
    const reachable=[];
    const selector=route==='Metodologia'?'.fan-document-links>a':route==='Previsões'?'.st-key-prediction-after .fan-timeline-stage':null;
    if(selector){
     const items=surface.locator(selector);
     requireCheck(await items.count()>0,'Missing scroll-access targets');
     for(let i=0;i<await items.count();i++){
      await items.nth(i).scrollIntoViewIfNeeded();await page.waitForTimeout(150);
      const hit=await items.nth(i).evaluate(el=>{
       const main=document.querySelector('.stMain').getBoundingClientRect(),dock=document.querySelector('.st-key-journey-navigation').getBoundingClientRect();
       const rects=Array.from(el.getClientRects()).filter(r=>r.width>0&&r.height>0&&r.top>=main.top&&r.bottom<=main.bottom&&r.left>=main.left&&r.right<=main.right);
       const r=rects.sort((a,b)=>b.width*b.height-a.width*a.height)[0];
       if(!r)return{label:el.innerText,accessible:false};
       const target=document.elementFromPoint((r.left+r.right)/2,(r.top+r.bottom)/2);
       return{label:el.innerText,accessible:main.bottom<=innerHeight+1&&!!target&&(target===el||el.contains(target)),rect:{x:r.x,y:r.y,right:r.right,bottom:r.bottom}};
      });
      reachable.push(hit);requireCheck(hit.accessible,'Scrolled item is clipped or covered: '+hit.label);
     }
    }
    await surface.locator('.stMain').evaluate(main=>main.scrollTo({top:0,behavior:'instant'}));
    await page.waitForTimeout(150);
    await page.screenshot({path:path.join(output,key+'.png')});
    evidence.push({route,lang,mobile,browser:browserName,status:'passed',photo_sha256:photoHash,measurements:m,reachable});
    fs.writeFileSync(path.join(output,'acceptance.json'),JSON.stringify({version,css_sha256:cssHash,cases:evidence},null,2));
    console.log(key+' passed');
   }catch(error){await page.screenshot({path:path.join(output,key+'-failure.png')});throw Error(key+': '+error.message);}
   finally{await context.close();}
  }
 }finally{await browser.close();}
 console.log(JSON.stringify({status:'passed',version,cases:evidence.length}));
})().catch(error=>{console.error(error);process.exit(1);});
