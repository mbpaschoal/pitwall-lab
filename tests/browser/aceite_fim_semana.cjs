/* PT/EN: Observed weekend data must agree across summary, weather and standings. */
const fs=require('node:fs'),path=require('node:path');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const [base,output]=process.argv.slice(2);
if(!base||!output)throw Error('Usage: node aceite_fim_semana.cjs URL OUTPUT');
const state=JSON.parse(fs.readFileSync(path.join(__dirname,'../../frontend_assets/operacao_fim_semana.json'),'utf8'));
const race=state.sessoes.find(s=>s.nome==='Race');
const check=(ok,message)=>{if(!ok)throw Error(message);};
fs.mkdirSync(output,{recursive:true});
(async()=>{
 if(!race?.encerramento_observado_utc||!race.tempos?.length){
  fs.writeFileSync(path.join(output,'acceptance.json'),JSON.stringify({status:'not-applicable',reason:'No observed main-race result'}));return;
 }
 const launch={headless:true};if(process.env.PLAYWRIGHT_CHANNEL)launch.channel=process.env.PLAYWRIGHT_CHANNEL;
 const browser=await chromium.launch(launch),cases=[];
 try{for(const mobile of [false,true])for(const lang of ['pt','en']){
  const context=await browser.newContext({viewport:mobile?{width:390,height:844}:{width:1440,height:1100},isMobile:mobile,hasTouch:mobile});
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  const key=(mobile?'mobile':'desktop')+'-'+lang;
  async function open(route){
   await page.goto(base+'/?'+new URLSearchParams({tela:route,temporada:String(state.temporada),gp:String(state.rodada),lang}));
   let surface=page;
   if(!/^https?:\/\/(127\.0\.0\.1|localhost)(:|\/)/.test(base)){
    await page.waitForFunction(()=>Array.from(document.querySelectorAll('iframe')).some(i=>i.src.includes('/~/+/')),null,{timeout:60000});
    for(let i=0;i<15&&!page.frames().some(f=>f.url().includes('/~/+/'));i++)await page.waitForTimeout(1000);
    surface=page.frames().find(f=>f.url().includes('/~/+/'));
   }
   await surface.locator('.fan-hero h1').waitFor({timeout:90000});
   await surface.waitForFunction(()=>document.querySelector('.stApp')?.getAttribute('data-test-script-state')==='notRunning',null,{timeout:90000});
   check(await surface.locator('[data-testid="stException"]').count()===0,'Application exception');return surface;
  }
  function podiumExpected(){return [2,1,3].map(position=>race.tempos.find(r=>r.posicao===position)?.piloto_id);}
  function temperature(field){const n=race.clima_observado.campos[field].media_amostras.toFixed(1);return lang==='pt'?n.replace('.',','):n;}
  try{
   let surface=await open('Corridas');
   const ids=await surface.locator('.fan-podium-place .fan-portrait').evaluateAll(images=>images.map(i=>i.dataset.driverId));
   check(JSON.stringify(ids)===JSON.stringify(podiumExpected()),'Summary podium differs from observed positions');
   if(race.clima_observado?.campos.air_temperature.elegivel)check((await surface.locator('.fan-weather strong').innerText()).includes(temperature('air_temperature')),'Summary uses forecast instead of observed race air');
   await page.screenshot({path:path.join(output,key+'-summary.png')});
   await surface.locator('.fan-gp-tabs').getByRole('link',{name:lang==='pt'?'Clima':'Weather',exact:true}).click();
   await surface.getByRole('heading',{name:lang==='pt'?'Clima observado durante a corrida':'Observed race weather',exact:true}).waitFor({timeout:60000});
   const metrics=(await surface.locator('[data-testid="stMetricValue"]').allTextContents()).map(s=>s.replace(',','.'));
   for(const field of ['air_temperature','track_temperature']){
    const measurement=race.clima_observado.campos[field];
    check(metrics.some(s=>measurement.elegivel?s.includes(measurement.media_amostras.toFixed(1)):s.trim()==='—'),'Observed temperature or explicit withholding missing: '+field);
   }
   await page.screenshot({path:path.join(output,key+'-weather.png')});
   surface=await open('Previsões');
   check(await surface.locator('.fan-podium-compact').count()===1,'Observed before/after comparison missing');
   check((await surface.locator('.fan-probability-row').count())>=3,'Recorded forecast missing');
   await page.screenshot({path:path.join(output,key+'-forecast.png')});
   surface=await open('Campeonato');
   const expected=Object.values(state.campeonatos||{}).filter(t=>t.disponivel).reduce((n,t)=>n+t.classificacao.length,0);
   check(await surface.locator('.tabela-editorial tbody tr').count()===expected,'Round-specific standings truncated or stale');
   check(errors.length===0,errors.join('; '));
   cases.push({lang,mobile,status:'passed',season:state.temporada,round:state.rodada,podium:ids,standings:expected});
   fs.writeFileSync(path.join(output,'acceptance.json'),JSON.stringify({status:'passed',cases},null,2));console.log(key+' passed');
  }catch(error){await page.screenshot({path:path.join(output,key+'-failure.png')});throw error;}
  finally{await context.close();}
 }}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
