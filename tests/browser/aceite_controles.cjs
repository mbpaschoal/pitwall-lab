/* PT/EN: language controls, sidebar selection and aligned native disclosures. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const pw=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const [base,out]=process.argv.slice(2),engine=process.env.PLAYWRIGHT_BROWSER||'chromium';
assert(base&&out,'Usage: aceite_controles.cjs URL OUTPUT');fs.mkdirSync(out,{recursive:true});
const version=fs.readFileSync(path.resolve(__dirname,'../../VERSION'),'utf8').trim();
const report={version,engine,base,cases:[]};
async function settleLanguage(app,lang,tela){
 await app.waitForFunction(({lang,tela})=>{
  const q=new URL(location.href).searchParams;
  return document.documentElement.lang===lang&&document.querySelector('.stApp')?.dataset.testScriptState==='notRunning'&&q.get('lang')===lang&&q.get('tela')===tela&&q.get('gp')==='19'&&q.get('temporada')==='2026'&&document.querySelectorAll('.st-key-pw-sidebar-menu button').length===15;
 },{lang,tela},{timeout:45000});
}
async function flagTarget(button){
 return button.evaluate(el=>{const r=el.getBoundingClientRect(),hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return{width:r.width,height:r.height,left:r.left,top:r.top,right:r.right,bottom:r.bottom,viewport_width:innerWidth,viewport_height:innerHeight,hit:!!hit&&(hit===el||el.contains(hit)),font:getComputedStyle(el.querySelector('p')||el).fontSize};});
}
async function activeMarker(app){
 await app.waitForFunction(()=>document.querySelector('.st-key-pw-sidebar-menu details')?.dataset.pwReady==='true');
 const menu=app.locator('.st-key-pw-sidebar-menu details');
 if(!await menu.evaluate(e=>e.open))await menu.locator('summary').click();
 const selected=app.locator('.st-key-pw-sidebar-menu button[kind="primary"]');
 await selected.scrollIntoViewIfNeeded();
 return selected.evaluate(el=>({text:el.innerText,height:el.getBoundingClientRect().height,border:getComputedStyle(el).borderLeftWidth,color:getComputedStyle(el).borderLeftColor,align:getComputedStyle(el.querySelector('p')).textAlign}));
}
(async()=>{const opts={headless:true};if(engine==='chromium'&&process.env.PLAYWRIGHT_CHANNEL)opts.channel=process.env.PLAYWRIGHT_CHANNEL;const b=await pw[engine].launch(opts);try{
for(const width of [390,1440])for(const lang of ['pt','en'])for(const tela of ['Corridas','Pilotos','Campeonato','Previsões','Desempenho','Metodologia']){
 const c=await b.newContext({viewport:{width,height:844},isMobile:width===390,hasTouch:width===390}),p=await c.newPage();const errors=[];p.on('pageerror',e=>errors.push(e.message));
 const row={width,lang,tela};try{
 await p.goto(base+'/?'+new URLSearchParams({tela,temporada:'2026',gp:'19',lang}),{waitUntil:'domcontentloaded',timeout:90000});
 let app=p;if(base.includes('streamlit.app')){for(let n=0;n<120;n++){app=p.frames().find(f=>f.url().includes('/~/+/'));if(app)break;await p.waitForTimeout(500);}assert(app,'App frame');}
 await app.waitForFunction(({lang,version,tela})=>document.querySelector('.stApp')?.dataset.testScriptState==='notRunning'&&document.documentElement.lang===lang&&document.querySelectorAll('.st-key-pw-sidebar-menu button').length===15&&document.querySelectorAll('[data-testid=stSelectbox]').length>=2&&document.querySelector('.st-key-journey-header')?.innerText.includes('v'+version)&&new URL(location.href).searchParams.get('tela')===tela,{lang,version,tela},{timeout:90000});
 await app.evaluate(()=>document.fonts.ready);await p.waitForTimeout(700);
 row.languageTargets=[];row.edgeClicks=[];
 for(const code of ['pt','en']){
  const target=await flagTarget(app.getByRole('button',{name:code==='pt'?/🇧🇷/:/🇬🇧/}));row.languageTargets.push({language:code,...target});
  assert(target.width>=44&&target.height>=50&&target.left>=0&&target.right<=width&&target.top>=0&&target.bottom<=target.viewport_height&&target.hit,'Language target must be reachable and at least 44x50px');
 }
 for(const [code,edge] of [[lang==='pt'?'en':'pt','left'],[lang,'right']]){
  const button=app.getByRole('button',{name:code==='pt'?/🇧🇷/:/🇬🇧/}),box=await button.boundingBox();
  const position={x:edge==='left'?2:box.width-2,y:box.height/2};
  if(width===390)await button.tap({position});else await button.click({position});
  await settleLanguage(app,code,tela);row.edgeClicks.push({language:code,edge,position});
 }
 row.activeMarker=await activeMarker(app);
 assert.equal(row.activeMarker.align,'left');assert.equal(row.activeMarker.border,'3px');
 assert(row.activeMarker.height>=(width===390?44:36),'Navigation target too small');
 const items=app.locator('[data-testid=stExpander] summary');row.expanders=[];
 for(let n=0;n<await items.count();n++){const item=items.nth(n);if(!await item.isVisible())continue;await item.scrollIntoViewIfNeeded();await p.waitForTimeout(60);const m=await item.evaluate(el=>{const p=el.querySelector('[data-testid=stMarkdownContainer] p'),i=el.querySelector('[data-testid=stIconMaterial]');if(!p||!i)return null;const a=p.getBoundingClientRect(),b=i.getBoundingClientRect();return{text:p.innerText,height:el.getBoundingClientRect().height,delta:Math.abs((a.top+a.bottom-b.top-b.bottom)/2),margin:getComputedStyle(p).marginBottom};});if(m){row.expanders.push(m);assert(m.height>=44&&m.delta<1.5&&parseFloat(m.margin)===0,'Expander misaligned: '+JSON.stringify(m));}}
 if(await items.filter({visible:true}).count()){const first=items.filter({visible:true}).first();await first.click();await p.waitForTimeout(120);await first.click();}
 assert.equal(await app.locator('[data-testid=stException]').count(),0);assert.equal(await app.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);assert.deepEqual(errors,[]);
 if(tela==='Pilotos'){await items.filter({visible:true}).first().scrollIntoViewIfNeeded();await p.screenshot({path:path.join(out,`${width}-${lang}-expanders.jpg`),type:'jpeg',quality:75});}
 row.status='passed';
 }catch(e){row.status='failed';row.error=e.message;await p.screenshot({path:path.join(out,`${width}-${lang}-${tela}-failure.jpg`),type:'jpeg',quality:70}).catch(()=>{});}finally{report.cases.push(row);fs.writeFileSync(path.join(out,'controls.json'),JSON.stringify(report,null,2));await c.close();}
}
}finally{await b.close();}assert(report.cases.every(x=>x.status==='passed'),JSON.stringify(report.cases.filter(x=>x.status==='failed')));})().catch(e=>{console.error(e);process.exitCode=1});
