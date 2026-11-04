/* PT/EN: documentary compound provenance and session isolation, with real CSVs. */
const fs=require('node:fs'),path=require('node:path');
const {selectComboboxOption}=require('./select_combobox.cjs');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const [base,output]=process.argv.slice(2);
if(!base||!output)throw Error('Usage: node aceite_pneus_lawson.cjs URL OUTPUT');
const version=fs.readFileSync(path.join(__dirname,'../../VERSION'),'utf8').trim();
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
 const launch={headless:true};if(process.env.PLAYWRIGHT_CHANNEL)launch.channel=process.env.PLAYWRIGHT_CHANNEL;
 const browser=await chromium.launch(launch),cases=[];
 try{for(const mobile of [false,true])for(const lang of ['pt','en']){
  const context=await browser.newContext({viewport:mobile?{width:390,height:844}:{width:1440,height:1100},isMobile:mobile,hasTouch:mobile});
  const page=await context.newPage(),key=(mobile?'mobile':'desktop')+'-'+lang;
  try{
   await page.goto(base+'/?'+new URLSearchParams({tela:'Corridas',temporada:'2026',gp:'19',lang}),{waitUntil:'domcontentloaded',timeout:60000});
   let app=page;
   if(!/^https?:\/\/(127\.0\.0\.1|localhost)(:|\/)/.test(base)){
    await page.waitForFunction(()=>Array.from(document.querySelectorAll('iframe')).some(i=>i.src.includes('/~/+/')),null,{timeout:60000});
    for(let n=0;n<30&&!page.frames().some(f=>f.url().includes('/~/+/'));n++)await page.waitForTimeout(500);
    app=page.frames().find(f=>f.url().includes('/~/+/'));
   }
   const idle=async()=>app.waitForFunction(()=>document.querySelector('.stApp')?.getAttribute('data-test-script-state')==='notRunning',null,{timeout:60000});
   await app.getByText('v'+version,{exact:true}).first().waitFor({timeout:90000});
   await app.locator('.fan-gp-tabs').getByRole('link',{name:lang==='pt'?'Pneus e paradas':'Tyres and stops',exact:true}).click();
   const select=app.locator('.st-key-acervo_2026_19_prova_pneus');
   await select.getByRole('combobox').waitFor({timeout:60000});await idle();
   check(await select.getByRole('combobox').inputValue()===(lang==='pt'?'Corrida':'Race'),'Race is not the default tyre session');
   await selectComboboxOption(app,select.getByRole('combobox'),lang==='pt'?'TL3':'FP3');
   await app.getByText(lang==='pt'?/^Lawson no TL3: médios/:/^Lawson in FP3: mediums/).waitFor({timeout:60000});
   await idle();
   check(await app.getByRole('link',{name:lang==='pt'?'GP Tempo · pneus de Lawson no TL3':"GP Tempo · Lawson's FP3 tyres",exact:true}).count()===1,'Clickable GP Tempo source missing');
   check(await app.getByRole('link',{name:lang==='pt'?'FIA · trechos em pista no TL3':'FIA · FP3 on-track runs',exact:true}).count()===1,'Clickable FIA source missing');
   await app.locator('summary').filter({hasText:lang==='pt'?'Detalhes dos stints e qualidade dos dados':'Stint details and data quality'}).click();
   async function download(suffix){
    const button=app.locator('.st-key-acervo_2026_19_csv_'+suffix).getByRole('button',{includeHidden:true});
    const details=button.locator('xpath=ancestor::details[1]');
    if(!await details.evaluate(e=>e.open))await details.locator('summary').click();
    const pending=page.waitForEvent('download');await button.click();
    const file=await pending,target=path.join(output,key+'-'+suffix+'.csv');await file.saveAs(target);
    return parseCSV(fs.readFileSync(target,'utf8'));
   }
   const table=await download('stints'),head=table[0];
   const driver=head.indexOf(lang==='pt'?'Piloto':'Driver');
   const rows=table.slice(1).filter(r=>r[driver]==='Liam LAWSON');
   check(rows.length===5,'Lawson must have five stints');
   const first=rows.find(r=>Number(r[head.indexOf('Stint')])===1);
   const col=(pt,en)=>head.indexOf(lang==='pt'?pt:en);
   check(first[col('Composto','Compound')]==='MEDIUM','Opening compound is not MEDIUM');
   check(Number(first[col('Volta inicial publicada','Published start lap')])===1&&Number(first[col('Volta final publicada','Published end lap')])===8,'Wrong reconstructed run bounds');
   check(first[col('Idade inicial do pneu','Initial tyre age')]==='','Unknown initial tyre age was invented');
   check(first[col('Origem do composto','Compound provenance')]===(lang==='pt'?'Conferência documental':'Documentary review'),'Documentary origin missing from CSV');
   check(first[col('Fonte complementar','Additional source')].includes('gp-tempo.com/api/laps'),'Alternative source missing from CSV');
   const pits=await download('paradas');check(pits.length===89,'FP3 must contain 88 session-specific pit passages');
   await app.getByText(lang==='pt'?/^Lawson no TL3: médios/:/^Lawson in FP3: mediums/).scrollIntoViewIfNeeded();
   await page.screenshot({path:path.join(output,key+'-fp3.png'),fullPage:false});
   await selectComboboxOption(app,select.getByRole('combobox'),lang==='pt'?'Corrida':'Race');
   await app.getByRole('heading',{name:lang==='pt'?'Pit stops da corrida principal':'Main-race pit stops',exact:true}).waitFor({timeout:60000});
   await idle();
   check(await app.getByText(lang==='pt'?/^Lawson no TL3: médios/:/^Lawson in FP3: mediums/).count()===0,'FP3 review leaked into the race view');
   check(await app.locator('[data-testid="stException"]').count()===0,'Application exception');
   cases.push({lang,mobile,status:'passed',version,lawson_stints:5,opening_compound:'MEDIUM',bounds:[1,8],initial_age:null,fp3_pit_passages:88,clickable_sources:2});
   fs.writeFileSync(path.join(output,'acceptance.json'),JSON.stringify({status:'passed',cases},null,2)+'\n');
   console.log(key+' passed');
  }catch(error){await page.screenshot({path:path.join(output,key+'-failure.png')});throw error;}
  finally{await context.close();}
 }}finally{await browser.close();}
})().catch(error=>{console.error(error.message);process.exit(1)});
