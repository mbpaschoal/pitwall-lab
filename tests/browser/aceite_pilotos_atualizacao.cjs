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
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHANNEL?{channel:process.env.PLAYWRIGHT_CHANNEL}:{})}),cases=[];
 try{for(const mobile of [false,true])for(const lang of ['pt','en']){
  const context=await browser.newContext(mobile?{...devices['Pixel 7'],viewport:{width:390,height:844}}:{viewport:{width:1440,height:1100}});
  const page=await context.newPage(),key=(mobile?'mobile':'desktop')+'-'+lang;let reloads=0;
  try{
   async function open(params){
    await page.goto(base+'/?'+new URLSearchParams({tela:'Pilotos',temporada:'2026',gp:'19',lang,...params}),{waitUntil:'domcontentloaded',timeout:60000});
    for(let attempt=0;attempt<2;attempt++){
     const app=base.startsWith('http://127.')?page:page.frameLocator('iframe[src*="/~/+/"]').first();
     try{
      await app.getByText('v'+version,{exact:true}).first().waitFor({timeout:60000});
      await app.locator('.fan-hero h1').waitFor({timeout:60000});
      await app.locator('.stApp[data-test-script-state="notRunning"]').waitFor({timeout:60000});
      check(await app.locator('[data-testid="stException"]').count()===0,'App exception');return app;
     }catch(error){if(attempt)throw error;reloads++;await page.reload({waitUntil:'domcontentloaded',timeout:60000});}
    }
   }
   let app=await open({visao:'perfil',piloto:'max_verstappen'});
   check((await app.locator('[data-testid="stCaptionContainer"]').allTextContents()).some(x=>x.includes(cutoff)),'Missing Mexico coverage');
   check((await app.locator('[data-testid="stMetricValue"]').first().innerText())===String(maxStarts),'Stale Max starts');
   await app.locator('.st-key-csv_max_verstappen').evaluate(e=>e.scrollIntoView({block:'center'}));
   const csvButton=app.locator('.st-key-csv_max_verstappen button');
   await csvButton.waitFor({state:'visible',timeout:45000});
   const [csv]=await Promise.all([page.waitForEvent('download'),csvButton.click()]);const csvPath=path.join(output,key+'-max.csv');await csv.saveAs(csvPath);
   const raw=fs.readFileSync(csvPath,'utf8');check(raw.includes('Mexico')&&raw.includes('gp=19'),'Mexico missing from exported evidence');
   await app.getByText(lang==='pt'?'Compartilhar esta análise':'Share this analysis',{exact:true}).click();
   await app.locator('.st-key-share_svg').evaluate(e=>e.scrollIntoView({block:'center'}));
   const svgButton=app.locator('.st-key-share_svg button');
   await svgButton.waitFor({state:'visible',timeout:45000});
   const [svg]=await Promise.all([page.waitForEvent('download'),svgButton.click()]);
   const svgPath=path.join(output,key+'-card.svg');await svg.saveAs(svgPath);check(fs.readFileSync(svgPath,'utf8').includes(cutoff),'Stale shared cutoff');
   await page.screenshot({path:path.join(output,key+'-max.png')});
   app=await open({visao:'perfil',piloto:'ryo_hirakawa',anos:'2026'});
   check((await app.locator('.fan-hero h1').innerText()).includes('Hirakawa'),'Driver identity replaced');
   const picture=app.locator('.fan-hero-image');await picture.evaluate(img=>img.decode());
   const image=await picture.evaluate(img=>({src:img.currentSrc,width:img.naturalWidth,height:img.naturalHeight}));
   check(image.width===source.width&&image.height===source.height,'Wrong original portrait resolution');
   check(crypto.createHash('sha256').update(Buffer.from(image.src.split(',')[1],'base64')).digest('hex')===source.sha256,'Wrong Hirakawa portrait');
   check(await app.locator('a.fan-art-label[href*="haasf1team.com"]').count()===1,'Incorrect portrait attribution');
   await page.screenshot({path:path.join(output,key+'-hirakawa.png')});
   app=await open({visao:'duelo',piloto:'max_verstappen',rival:'alonso',anos:'2026'});
   check(await app.locator('[data-testid="stException"]').count()===0,'Duel exception');
   const denominator=app.locator('[data-testid="stCaptionContainer"]').filter({hasText:new RegExp(common.length+' (largadas em comum|shared starts)','i')}).first();
   await denominator.waitFor({timeout:30000});
   check((await denominator.innerText()).includes(String(comparable)),'Wrong comparable-result denominator');
   const metrics=await app.locator('[data-testid="stMetric"]').allTextContents();
   cases.push({lang,mobile,version,reloads,maxStarts,csv:true,svg:true,hirakawa_original_sha256:source.sha256,duel_metrics:metrics,status:'passed'});
   fs.writeFileSync(path.join(output,'acceptance.json'),JSON.stringify({status:'passed',cases},null,2)+'\n');console.log(key+' passed');
  }catch(e){await page.screenshot({path:path.join(output,key+'-failure.png')});throw e;}finally{await context.close();}
 }}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
