/* Complete immutable artwork in the actual served app, across all 26 venues. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const pw=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const {surface}=require('./app_surface.cjs'),{verifyImage,ready}=require('./verificar_publicacao.cjs');
const [base,output]=process.argv.slice(2);assert(base&&output,'Usage: URL OUTPUT');
const root=path.resolve(process.env.PITWALL_SOURCE_ROOT||path.join(__dirname,'../../distribuicao/pitwall-dashboard'));
const catalog=JSON.parse(fs.readFileSync(path.join(root,'frontend_assets/destination_illustrations.json')));
const weekend=JSON.parse(fs.readFileSync(path.join(root,'frontend_assets/race_weekend.json')));
const version=fs.readFileSync(path.join(root,'VERSION'),'utf8').trim();
const events=new Map(weekend.dados_2026.corridas.map(r=>[r.circuito_id,[r.temporada,r.rodada]]));
for(const [cid,round] of [['bahrain',4],['jeddah',5],['imola',7]])events.set(cid,[2025,round]);
const engine=process.env.PLAYWRIGHT_BROWSER||'chromium';
const selected=process.env.PITWALL_ART_CIRCUITS?.split(',')||Object.keys(catalog.circuits);
const widths=process.env.PITWALL_ART_WIDTHS?.split(',').map(Number)||[1440,390];
fs.mkdirSync(output,{recursive:true});
(async()=>{
 assert.equal(catalog.complete,true);assert.equal(Object.keys(catalog.circuits).length,26);
 const options={headless:true};if(engine==='chromium'&&process.env.PLAYWRIGHT_CHANNEL)options.channel=process.env.PLAYWRIGHT_CHANNEL;
 const browser=await pw[engine].launch(options),report={base,engine,version,cases:[]};
 const save=()=>fs.writeFileSync(path.join(output,'acceptance.json'),JSON.stringify(report,null,2));
 try{for(const cid of selected)for(const width of widths){
  const lang=width===1440?'pt':'en',event=events.get(cid);assert(event,'Unknown event '+cid);
  const context=await browser.newContext({viewport:{width,height:1000},isMobile:width<600,hasTouch:width<600});
  const page=await context.newPage(),errors=[],row={cid,width,lang,event};report.cases.push(row);page.on('pageerror',e=>errors.push(e.message));
  try{
   await page.goto(base+'/?'+new URLSearchParams({tela:'Corridas',temporada:event[0],gp:event[1],lang}),{waitUntil:'domcontentloaded'});
   const app=await surface(page,base);await ready(app,version,lang,'Corridas');
   const art=catalog.circuits[cid];
   row.image=await verifyImage(page,app,{...art,kind:'gouache',static_path:art.path,selector:'.pw-postcard[data-place="'+cid+'"] .pc-illustration'});
   assert.equal(await app.locator('.pc-photo').count(),0,'Old split cover returned');
   row.frame=await app.locator('.pc-illustration').evaluate(e=>{
    const r=e.getBoundingClientRect(),scene=e.closest('.pc-scene').getBoundingClientRect();
    const parents=[];for(let p=e.parentElement;p&&!p.classList.contains('stMain');p=p.parentElement){const s=getComputedStyle(p),b=p.getBoundingClientRect();if(['hidden','clip'].includes(s.overflowY)||['hidden','clip'].includes(s.overflowX))parents.push({x:b.x,y:b.y,right:b.right,bottom:b.bottom});}
    return{x:r.x,y:r.y,right:r.right,bottom:r.bottom,scene:{x:scene.x,right:scene.right},parents,viewport:innerWidth};
   });
   const f=row.frame;assert(f.x>=0&&f.right<=f.viewport+1,'Image extends beyond viewport');
   for(const p of f.parents)assert(f.x>=p.x-1&&f.right<=p.right+1&&f.y>=p.y-1&&f.bottom<=p.bottom+1,'Ancestor clips artwork');
   assert.deepEqual(errors,[]);assert.equal(context.pages().length,1);
   await app.locator('.pc-illustration').scrollIntoViewIfNeeded();
   await page.screenshot({path:path.join(output,cid+'-'+width+'-'+lang+'.png')});row.status='passed';
  }catch(e){row.status='failed';row.error=e.stack;await page.screenshot({path:path.join(output,cid+'-'+width+'-failed.png')});throw e}
  finally{save();await context.close()}
  console.log(JSON.stringify(row));
 }}finally{await browser.close();save()}
})().catch(e=>{console.error(e);process.exit(1)});
