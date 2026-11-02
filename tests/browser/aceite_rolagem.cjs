/* PT/EN: real scroll clipping, foreground content and hit targets.
 * PLAYWRIGHT_BROWSER=chromium (default) or webkit; optional PLAYWRIGHT_CHANNEL.
 * Each route/language/viewport uses a fresh context and five scroll positions.
 * Hero photographs intentionally sit behind their headings; portraits never do.
 */
const fs=require('node:fs'),path=require('node:path');
const engines=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const browserName=process.env.PLAYWRIGHT_BROWSER||'chromium';
if(!['chromium','webkit'].includes(browserName))throw Error('Unsupported PLAYWRIGHT_BROWSER');
const expectedVersion=process.env.AUDIT_EXPECTED_VERSION||fs.readFileSync(path.join(__dirname,'../../VERSION'),'utf8').trim();
const [base,output]=process.argv.slice(2);
if(!base||!output)throw Error('Usage: node aceite_rolagem.cjs BASE_URL OUTPUT_DIR');
fs.mkdirSync(output,{recursive:true});
const routes=['Corridas','Pilotos','Campeonato','Previsões','Desempenho','Metodologia'];
const kinds=['race','drivers','championship','forecast','performance','method'];
const audit={utc:new Date().toISOString(),base,browser:browserName,expectedVersion,scope:'6 screens x PT/EN x 390x560 and 1440x900 x five scroll positions; header and pilot filter text2x; mobile resize',limitations:['Canvas/Plotly internals and cross-origin iframe text require separate functional tests.','Background hero images and foreground title overlays are intentional and excluded from image collisions.','Partly clipped lines at scroll-viewport edges and CSS-hidden accessibility labels are excluded.','Text2x doubles computed font-size/line-height as a deterministic reflow stress test; it is not native browser zoom.'],samples:[],stress:[]};
const launch={headless:true};if(browserName==='chromium'&&process.env.PLAYWRIGHT_CHANNEL)launch.channel=process.env.PLAYWRIGHT_CHANNEL;
const save=()=>fs.writeFileSync(path.join(output,'scroll-audit.json'),JSON.stringify(audit,null,2));
const doubleTextMetrics=surface=>surface.evaluate(async()=>{
 const metrics=Array.from(document.querySelectorAll('body *')).filter(n=>!['SCRIPT','STYLE','SVG','PATH'].includes(n.tagName)).map(n=>({n,size:parseFloat(getComputedStyle(n).fontSize),line:parseFloat(getComputedStyle(n).lineHeight)}));
 for(const {n,size,line} of metrics){if(size)n.style.setProperty('font-size',size*2+'px','important');if(line)n.style.setProperty('line-height',line*2+'px','important');}
 for(const icon of document.querySelectorAll('[data-testid="stIconMaterial"]')){const c=getComputedStyle(icon);await document.fonts.load(c.fontSize+' '+c.fontFamily,icon.textContent);}
 await document.fonts.ready;
 await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
 document.querySelector('.stMain').scrollTo({top:0,behavior:'instant'});
});
(async()=>{const browser=await engines[browserName].launch(launch);try{
for(const viewport of [{width:390,height:560},{width:1440,height:900}])for(const lang of ['pt','en'])for(const [index,route] of routes.entries()){
 const mobile=viewport.width===390,context=await browser.newContext({viewport,isMobile:mobile,hasTouch:mobile,deviceScaleFactor:1,reducedMotion:'reduce'}),page=await context.newPage();
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 const id=`${lang}-${viewport.width}x${viewport.height}-${route}`;
 const sampleStart=audit.samples.length,stressStart=audit.stress.length;
 try{
  await page.goto(base+'/?'+new URLSearchParams({tela:route,temporada:'2026',gp:'19',lang}),{waitUntil:'domcontentloaded',timeout:90000});
  let surface=page;
  if(base.includes('streamlit.app')){for(let i=0;i<120;i++){surface=page.frames().find(f=>f.url().includes('/~/+/'));if(surface)break;await page.waitForTimeout(500);}if(!surface)throw Error('Public application frame unavailable');}
  await surface.waitForFunction(kind=>document.querySelector('.fan-hero')?.dataset.heroKind===kind&&document.querySelector('.stApp')?.dataset.testScriptState==='notRunning',kinds[index],{timeout:90000});
  await surface.evaluate(async()=>{
     await document.fonts.ready;
     // Streamlit can introduce Material Symbols after the first fonts.ready.
     // Load those faces explicitly instead of treating a fallback word as a glyph.
     for(const icon of document.querySelectorAll('[data-testid="stIconMaterial"]')){const c=getComputedStyle(icon);await document.fonts.load(c.fontSize+' '+c.fontFamily,icon.textContent);}
     await document.fonts.ready;
     await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
    });
    await surface.waitForFunction(expected=>document.documentElement.lang===expected,lang,{timeout:15000});await page.waitForTimeout(650);
  for(const fraction of [0,.25,.5,.75,1]){
   await surface.locator('.stMain').evaluate((main,f)=>main.scrollTo({top:f*(main.scrollHeight-main.clientHeight),behavior:'instant'}),fraction);await page.waitForTimeout(250);
   const result=await surface.evaluate(({fraction,expectedLang,expectedVersion})=>{
    const issues=[],box=n=>{const r=n.getBoundingClientRect();return{x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height}},main=document.querySelector('.stMain'),dock=document.querySelector('.st-key-journey-navigation');
    if(!main||!dock)return{fraction,issues:[{kind:'missing_shell'}]};
    const m=box(main),d=box(dock),clip={x:Math.max(0,m.x),y:Math.max(0,m.y),right:Math.min(innerWidth,m.right),bottom:Math.min(innerHeight,m.bottom)};
    const rectsOverlap=(a,b)=>Math.min(a.right,b.right)-Math.max(a.x,b.x)>2&&Math.min(a.bottom,b.bottom)-Math.max(a.y,b.y)>2;
    const fullyVisible=r=>r.width>1&&r.height>1&&r.x>=clip.x+1&&r.right<=clip.right-1&&r.y>=clip.y+1&&r.bottom<=clip.bottom-1;
    const visible=n=>n&&n.getClientRects().length&&getComputedStyle(n).visibility!=='hidden'&&getComputedStyle(n).display!=='none';
    const painted=(r,node)=>{for(let p=node;p&&p!==main;p=p.parentElement){const c=getComputedStyle(p);if(c.opacity==='0'||c.visibility==='hidden'||c.display==='none'||c.contentVisibility==='hidden'||c.clipPath!=='none')return false;if(p.tagName==='DETAILS'&&!p.open&&!p.querySelector(':scope>summary')?.contains(node))return false;const pr=box(p);if(/hidden|clip|auto|scroll/.test(c.overflowX)&&(r.x<pr.x-.5||r.right>pr.right+.5))return false;if(/hidden|clip|auto|scroll/.test(c.overflowY)&&(r.y<pr.y-.5||r.bottom>pr.bottom+.5))return false}return true};
    if(m.bottom>d.y-4+.5)issues.push({kind:'scrollport_under_navigation',main:m,dock:d});
    if(document.querySelectorAll('h1').length!==1)issues.push({kind:'main_title_count',count:document.querySelectorAll('h1').length});
    for(const block of main.querySelectorAll('.st-key-race-summary,.stTabs:has(.fan-circuit-details),.fan-pilot-ranking,.st-key-fan-prediction-intro,.fan-results,.fan-process,.st-key-pilot-view-navigation,.fan-pilot-toolbar,.fan-condition-chips,.fan-photo-credits')){const c=getComputedStyle(block);if(visible(block)&&(parseFloat(c.marginTop)<0||parseFloat(c.marginBottom)<0||['fixed','absolute'].includes(c.position)))issues.push({kind:'content_leaves_normal_flow',className:block.className,marginTop:c.marginTop,marginBottom:c.marginBottom,position:c.position});}
    if(document.documentElement.scrollWidth>innerWidth+1)issues.push({kind:'page_horizontal_overflow',width:innerWidth,scrollWidth:document.documentElement.scrollWidth});
    if(document.documentElement.lang!==expectedLang)issues.push({kind:'wrong_language',actual:document.documentElement.lang,expected:expectedLang});
    const version=document.body.innerText.match(/\bv\d+\.\d+\.\d+/)?.[0];if(expectedVersion&&version!=='v'+expectedVersion)issues.push({kind:'wrong_version',version,expectedVersion});
    for(const [before,after,label] of [['.st-key-weekend-status','.st-key-race-summary','status_vs_race_summary'],['.st-key-weekend-status','.st-key-fan-prediction-intro','status_vs_forecast_intro'],['.st-key-pilot-favorite-control','.fan-pilot-ranking','favorite_vs_ranking']]){
     const a=document.querySelector(before),b=document.querySelector(after);if(visible(a)&&visible(b)){const ra=box(a),rb=box(b);if(ra.bottom>rb.y+.5)issues.push({kind:label,before:ra,after:rb});}
    }
    const excluded='.st-key-journey-navigation,.js-plotly-plot,script,style,noscript,[aria-hidden="true"],.pw-skip-link';
    const walker=document.createTreeWalker(main,NodeFilter.SHOW_TEXT),textBoxes=[];let n;
    while((n=walker.nextNode())){
     const el=n.parentElement;if(!n.textContent.trim()||!el||el.closest(excluded)||!visible(el))continue;
     const range=document.createRange();range.selectNodeContents(n);
     for(const rect of range.getClientRects()){
      const r={x:rect.x,y:rect.y,right:rect.right,bottom:rect.bottom,width:rect.width,height:rect.height};if(!fullyVisible(r)||!painted(r,el))continue;
      const x=(r.x+r.right)/2,y=(r.y+r.bottom)/2,hit=document.elementFromPoint(x,y);textBoxes.push({node:el,rect:r,text:n.textContent.trim().slice(0,90)});
      if(hit&&hit!==el&&!el.contains(hit)&&!hit.contains(el)&&issues.filter(v=>v.kind==='occluded_text').length<12)issues.push({kind:'occluded_text',text:n.textContent.trim().slice(0,90),rect:r,by:hit.tagName+'.'+hit.className});
     }
    }
    // Foreground portraits must not cover sibling text. Hero/background photos
    // are deliberately omitted; their title overlays are part of the identity.
    for(const image of main.querySelectorAll('img.fan-portrait')){
     if(!visible(image))continue;const ir=box(image);if(!fullyVisible(ir))continue;
     const card=image.closest('.fan-podium-place,.fan-condition-row,.fan-probability-row,.pilot-card,td,th');if(!card)continue;
     for(const text of textBoxes)if(card.contains(text.node)&&!text.node.contains(image)&&rectsOverlap(ir,text.rect)&&issues.filter(v=>v.kind==='portrait_over_text').length<8)issues.push({kind:'portrait_over_text',text:text.text,image:ir,textRect:text.rect});
    }
    for(const el of main.querySelectorAll('a,button,summary,select,[role="tab"]')){
     if(el.closest(excluded)||!visible(el)||el.disabled)continue;const rs=[...el.getClientRects()].map(v=>({x:v.x,y:v.y,right:v.right,bottom:v.bottom,width:v.width,height:v.height})).filter(v=>fullyVisible(v)&&painted(v,el));const r=rs.sort((a,b)=>b.width*b.height-a.width*a.height)[0];if(!r||r.width<8||r.height<8)continue;
     const hit=document.elementFromPoint((r.x+r.right)/2,(r.y+r.bottom)/2);
     if(hit&&hit!==el&&!el.contains(hit)&&issues.filter(v=>v.kind==='occluded_control').length<10)issues.push({kind:'occluded_control',label:(el.innerText||el.getAttribute('aria-label')||el.tagName).slice(0,90),rect:r,by:hit.tagName+'.'+hit.className});
    }
    for(const label of dock.querySelectorAll('[role="radiogroup"]>label')){
     const r=box(label),hit=document.elementFromPoint((r.x+r.right)/2,(r.y+r.bottom)/2);
     if(r.width<44||r.height<44||r.x<0||r.right>innerWidth+1||r.y<0||r.bottom>innerHeight+1)issues.push({kind:'navigation_target_clipped_or_small',label:label.innerText,rect:r});
     if(hit&&hit!==label&&!label.contains(hit))issues.push({kind:'navigation_target_occluded',label:label.innerText,by:hit.tagName+'.'+hit.className});
    }
    if(document.querySelector('[data-testid="stException"]'))issues.push({kind:'streamlit_exception',text:document.querySelector('[data-testid="stException"]').innerText});
    return{fraction,version,main:m,dock:d,clip,scrollTop:main.scrollTop,scrollHeight:main.scrollHeight,visibleTextFragments:textBoxes.length,issues};
   },{fraction,expectedLang:lang,expectedVersion});
   result.route=route;result.lang=lang;result.viewport=viewport;result.frontendErrors=[...errors];if(errors.length)result.issues.push({kind:'frontend_exception',errors:[...errors]});audit.samples.push(result);save();
   if(result.issues.length||fraction===1)await page.screenshot({path:path.join(output,`${id}-${fraction}.jpg`),type:'jpeg',quality:65,scale:'css'});
  }
  if(route==='Corridas'){
   // The header is shared by all six screens. Test text reflow separately from
   // the photographs' 2x source-resolution contract in aceite_visual.cjs.
   await doubleTextMetrics(surface);
   await page.waitForTimeout(450);
   const controls=surface.locator('.st-key-journey-context-row [data-baseweb="select"]');
   const reflow={route,lang,viewport,type:'shared_header_text2x',controls:[],issues:[]};
   for(let i=0;i<await controls.count();i++){
    await controls.nth(i).scrollIntoViewIfNeeded();await page.waitForTimeout(100);
    const result=await controls.nth(i).evaluate(el=>{
     const box=n=>{const r=n.getBoundingClientRect();return{x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height};};
     const main=box(document.querySelector('.stMain')),dock=box(document.querySelector('.st-key-journey-navigation')),control=box(el),value=el.querySelector('div[value]'),issues=[];
     if(main.bottom>dock.y-4+.5)issues.push({kind:'scrollport_under_navigation',main,dock});
     if(!value)return{issues:[...issues,{kind:'selected_value_missing'}],main,dock,control};
     const selected=box(value),range=document.createRange();range.selectNodeContents(value);
     const fragments=Array.from(range.getClientRects()).filter(r=>r.width>0&&r.height>0).map(r=>({x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height}));
     const inside=(r,b)=>r.x>=b.x-1&&r.right<=b.right+1&&r.y>=b.y-1&&r.bottom<=b.bottom+1;
     if(selected.width<1||!fragments.length||fragments.some(r=>!inside(r,control)||!inside(r,main)))issues.push({kind:'selected_value_clipped_text2x',value:value.innerText,selected,control,fragments});
     return{value:value.innerText,main,dock,control,selected,fragments,issues};
    });
    reflow.controls.push(result);reflow.issues.push(...result.issues);
   }
   if(await controls.count()!==2)reflow.issues.push({kind:'context_selector_count',count:await controls.count()});
   audit.stress.push(reflow);save();
   await page.screenshot({path:path.join(output,`${id}-text2x.jpg`),type:'jpeg',quality:65,scale:'css'});
   if(mobile)for(const height of [400,700,560]){
    await page.setViewportSize({width:viewport.width,height});await page.waitForTimeout(300);
    const resize=await surface.evaluate(()=>{const rect=n=>{const r=n.getBoundingClientRect();return{y:r.y,bottom:r.bottom,height:r.height};},main=rect(document.querySelector('.stMain')),dock=rect(document.querySelector('.st-key-journey-navigation'));return{main,dock,viewport:[innerWidth,innerHeight],issues:main.bottom<=dock.y-4+.5?[]:[{kind:'scrollport_under_navigation_after_resize',main,dock}]};});
    audit.stress.push({route,lang,type:'text2x_mobile_resize',...resize});save();
   }
  }
  if(route==='Pilotos'){
   await surface.waitForFunction(()=>{if(document.querySelector('.stApp')?.dataset.testScriptState!=='notRunning'){window.pwAuditIdleSince=0;return false;}window.pwAuditIdleSince||=performance.now();return performance.now()-window.pwAuditIdleSince>=1000;},null,{timeout:45000});
   const filter=surface.getByRole('button',{name:lang==='pt'?'Filtros':'Filters',exact:false});
   const baselineLabelFontSize=await filter.locator('p').evaluate(label=>parseFloat(getComputedStyle(label).fontSize));
   await doubleTextMetrics(surface);await page.waitForTimeout(250);
   await filter.scrollIntoViewIfNeeded();
   const result=await filter.evaluate((button,baselineLabelFontSize)=>{
    const box=n=>{const r=n.getBoundingClientRect();return{x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height};},rangeBox=n=>{const r=document.createRange();r.selectNodeContents(n);const b=r.getBoundingClientRect();return{x:b.x,y:b.y,right:b.right,bottom:b.bottom,width:b.width,height:b.height};};
    const rect=box(button),main=box(document.querySelector('.stMain')),dock=box(document.querySelector('.st-key-journey-navigation')),icon=button.querySelector('[data-testid="stIconMaterial"]'),label=button.querySelector('p'),issues=[];
    const inside=(a,b)=>a.x>=b.x-1&&a.right<=b.right+1&&a.y>=b.y-1&&a.bottom<=b.bottom+1,overlap=(a,b)=>Math.min(a.right,b.right)-Math.max(a.x,b.x)>1&&Math.min(a.bottom,b.bottom)-Math.max(a.y,b.y)>1;
    const hit=document.elementFromPoint((rect.x+rect.right)/2,(rect.y+rect.bottom)/2);
    if(main.bottom>dock.y-4+.5||!inside(rect,main)||!hit||(hit!==button&&!button.contains(hit)))issues.push({kind:'pilot_filter_inaccessible_text2x',rect,main,dock});
    if(!icon||!label)return{issues:[...issues,{kind:'pilot_filter_parts_missing'}]};
    const slot=box(icon),glyph=rangeBox(icon),text=rangeBox(label),c=getComputedStyle(icon),labelFontSize=parseFloat(getComputedStyle(label).fontSize),fontLoaded=document.fonts.check(c.fontSize+' '+c.fontFamily,icon.textContent);
    if(!fontLoaded)issues.push({kind:'pilot_filter_icon_font_unavailable',font:c.fontFamily});
    if(labelFontSize<baselineLabelFontSize*2-.5)issues.push({kind:'text2x_reset_by_rerender',baselineLabelFontSize,labelFontSize});
    if(!inside(slot,rect)||!inside(glyph,rect)||!inside(text,rect)||glyph.width>slot.width+1||overlap(glyph,text))issues.push({kind:'pilot_filter_icon_over_text2x',rect,slot,glyph,text,font:c.fontFamily});
    const iconAncestors=[];for(let n=icon;n&&n!==button;n=n.parentElement){const s=getComputedStyle(n);iconAncestors.push({tag:n.tagName,className:n.className,rect:box(n),width:s.width,minWidth:s.minWidth,display:s.display,flex:s.flex,gap:s.gap});}
    return{rect,slot,glyph,text,iconAncestors,font:c.fontFamily,fontLoaded,baselineLabelFontSize,labelFontSize,issues};
   },baselineLabelFontSize);
   audit.stress.push({route,lang,viewport,type:'pilot_filter_text2x',...result});save();
   await page.screenshot({path:path.join(output,`${id}-filter-text2x.jpg`),type:'jpeg',quality:65,scale:'css'});
  }
  console.log(id+': '+[...audit.samples.slice(sampleStart),...audit.stress.slice(stressStart)].reduce((sum,s)=>sum+s.issues.length,0)+' issues');
 }catch(error){audit.samples.push({route,lang,viewport,status:'error',error:error.message,issues:[{kind:'audit_setup_or_navigation_error'}]});save();try{await page.screenshot({path:path.join(output,id+'-error.jpg'),type:'jpeg',quality:65,scale:'css'});}catch(_){}console.error(id+': '+error.message)}finally{await context.close()}
}
}finally{await browser.close();audit.finishedAt=new Date().toISOString();audit.status=[...audit.samples,...audit.stress].some(s=>s.issues?.length)?'failed':'passed';save()}
console.log(JSON.stringify({status:audit.status,samples:audit.samples.length,stress:audit.stress.length,issues:[...audit.samples,...audit.stress].reduce((sum,s)=>sum+(s.issues?.length||0),0)}));if(audit.status!=='passed')process.exitCode=1;
})().catch(error=>{console.error(error);process.exit(1)});
