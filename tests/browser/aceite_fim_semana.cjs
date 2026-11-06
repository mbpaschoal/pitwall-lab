const {choose,reveal}=require('./sidebar_navigation.cjs');
/* PT/EN: Observed weekend data must agree across summary, weather and standings. */
const fs=require('node:fs'),path=require('node:path');
const {selectComboboxOption}=require('./select_combobox.cjs');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const [base,output]=process.argv.slice(2);
if(!base||!output)throw Error('Usage: node aceite_fim_semana.cjs URL OUTPUT');
const state=JSON.parse(fs.readFileSync(path.join(__dirname,'../../frontend_assets/operacao_fim_semana.json'),'utf8'));
const race=state.sessoes.find(s=>s.nome==='Race');
const check=(ok,message)=>{if(!ok)throw Error(message);};
function parseCSV(text){
 return text.replace(/^\uFEFF/,'').trim().split(/\r?\n/).map(line=>{
  const cells=[];let cell='',quoted=false;
  for(let i=0;i<line.length;i++){const c=line[i];if(c==='"'){if(quoted&&line[i+1]==='"'){cell+='"';i++;}else quoted=!quoted;}else if(c===','&&!quoted){cells.push(cell);cell='';}else cell+=c;}
  cells.push(cell);return cells;
 });
}
fs.mkdirSync(output,{recursive:true});
(async()=>{
 if(!race?.encerramento_observado_utc||!race.tempos?.length){
  fs.writeFileSync(path.join(output,'acceptance.json'),JSON.stringify({status:'not-applicable',reason:'No observed main-race result'}));return;
 }
 const launch={headless:true};if(process.env.PLAYWRIGHT_CHANNEL)launch.channel=process.env.PLAYWRIGHT_CHANNEL;
 const browser=await chromium.launch(launch),cases=[];
 const save=()=>fs.writeFileSync(path.join(output,'acceptance.json'),JSON.stringify({status:cases.some(c=>c.status==='failed')?'failed':cases.length===4?'passed':'in_progress',cases},null,2)+'\n');
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
   await choose(surface,'weather');
   await surface.getByRole('heading',{name:lang==='pt'?'Clima observado durante a corrida':'Observed race weather',exact:true}).waitFor({timeout:60000});
   await surface.locator('[data-testid="stMetricValue"]').first().waitFor({timeout:60000});
   await surface.waitForFunction(()=>document.querySelector('.stApp')?.getAttribute('data-test-script-state')==='notRunning',null,{timeout:60000});
   const metrics=(await surface.locator('[data-testid="stMetricValue"]').allTextContents()).map(s=>s.replace(',','.'));
   for(const field of ['air_temperature','track_temperature']){
    const measurement=race.clima_observado.campos[field];
    check(metrics.some(s=>measurement.elegivel?s.includes(measurement.media_amostras.toFixed(1)):s.trim()==='—'),'Observed temperature or explicit withholding missing: '+field);
   }
   await page.screenshot({path:path.join(output,key+'-weather.png')});
   const qualifying=state.sessoes.find(s=>s.nome==='Qualifying');
   if(state.temporada===2026&&state.rodada===19&&qualifying?.revisao_fontes&&qualifying.tempos.some(r=>r.status==='DSQ')){
    await choose(surface,'sessions');
    await surface.getByRole('heading',{name:lang==='pt'?'Tempos de sessão':'Session times',exact:true}).waitFor({timeout:60000});
    const select=surface.locator('.st-key-acervo_2026_19_sessao_tempos').getByRole('combobox');
    async function downloadSession(option,suffix){
     const label=lang==='en'?({'TL3':'FP3','Corrida':'Race'}[option]||option):option;
     await selectComboboxOption(surface,select,label);
     const caption=option==='TL3'?(lang==='pt'?'Melhor volta publicada de cada piloto nesta sessão de treino.':"Each driver's published fastest lap in this practice session."):(option==='Corrida'?/^NC (indica|means)/:/^DSQ (indica|means)/);
     await surface.getByText(caption).waitFor({timeout:60000});
     await surface.waitForFunction(()=>document.querySelector('.stApp')?.getAttribute('data-test-script-state')==='notRunning',null,{timeout:60000});
     const button=surface.locator('.st-key-acervo_2026_19_csv_tempos').getByRole('button',{includeHidden:true});
     const expander=surface.locator('[data-testid="stExpander"]').filter({has:button}).getByText(lang==='pt'?'Exportar tabela':'Export table',{exact:true});
     if(!await expander.evaluate(e=>e.closest('details')?.open))await expander.click();
     const ready=page.waitForEvent('download');await button.click();
     const downloaded=await ready,target=path.join(output,key+'-'+suffix+'.csv');await downloaded.saveAs(target);return parseCSV(fs.readFileSync(target,'utf8'));
    }
    const fp3=await downloadSession('TL3','fp3');
    check(fp3.length===23,'FP3 must retain all 22 drivers');
    const lawson=fp3.slice(1).find(r=>r.some(c=>/Liam.*LAWSON/i.test(c)));
    check(lawson&&lawson[0]==='9'&&lawson.includes('1:18.113'),'Lawson FP3 identity/result not recovered');
    const q=await downloadSession(lang==='pt'?'Classificação':'Qualifying','qualifying');
    check(q.length===23,'Qualifying must retain all 22 drivers');
    const dq=q.slice(1).find(r=>r.some(c=>/Liam.*LAWSON/i.test(c)));
    check(dq&&dq[0]==='—'&&dq[q[0].indexOf(lang==='pt'?'Situação':'Status')]==='DSQ','Disqualification became a numeric rank');
    for(const phase of ['Q1','Q2','Q3'])check(dq[q[0].indexOf(phase)]==='—','Disqualified time shown as valid');
    await page.screenshot({path:path.join(output,key+'-qualifying-dsq.png')});
    if(race.tempos.some(r=>String(r.fonte_validacao||'').endsWith('_final_race_classification.pdf'))){
     const final=await downloadSession('Corrida','race-final');
     check(final.length===23,'Final race must retain all 22 drivers');
     for(const [driver,position,time] of [['PIASTRI','13','2:20:58.247'],['COLAPINTO','15','2:20:58.976'],['GASLY','17','2:21:20.255']]){
      const row=final.slice(1).find(r=>r.some(c=>c.toUpperCase().includes(driver)));
      check(row&&row[0]===position&&row.includes(time),'Final penalty result missing: '+driver);
     }
     const status=final[0].indexOf(lang==='pt'?'Situação':'Status');
     const nc=final.slice(1).filter(r=>r[status]==='NC');
     check(nc.length===5&&nc.every(r=>r[0]==='—'),'NC drivers gained invented finishing positions');
     const hirakawa=final.slice(1).find(r=>r.some(c=>c.includes('HIRAKAWA')));
     check(hirakawa&&hirakawa.includes('Haas F1 Team'),'Reviewed Hirakawa team missing');
     await page.screenshot({path:path.join(output,key+'-race-final.png')});
    }
   }
   surface=await open('Previsões');await reveal(surface,lang);
   check(await surface.locator('.fan-podium-compact').count()===1,'Observed before/after comparison missing');
   check(await surface.locator('.pw-tarot-prob').count()===3,'Recorded forecast missing');
   await page.screenshot({path:path.join(output,key+'-forecast.png')});
   surface=await open('Campeonato');
   const expected=Object.values(state.campeonatos||{}).filter(t=>t.disponivel).reduce((n,t)=>n+t.classificacao.length,0);
   check(await surface.locator('.tabela-editorial tbody tr').count()===expected,'Round-specific standings truncated or stale');
   check(errors.length===0,errors.join('; '));
   cases.push({lang,mobile,status:'passed',season:state.temporada,round:state.rodada,podium:ids,standings:expected});
   save();console.log(key+' passed');
  }catch(error){cases.push({lang,mobile,status:'failed',error:error.message});save();await page.screenshot({path:path.join(output,key+'-failure.png')}).catch(()=>{});throw error;}
  finally{await context.close();}
 }}finally{await browser.close();save();}
})().catch(e=>{console.error(e);process.exit(1);});
