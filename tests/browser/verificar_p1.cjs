/* Automatic forecast acceptance; actual observations and failed attempts retained. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const crypto=require('node:crypto');
const {ready}=require('./verificar_publicacao.cjs');

function checkPlot(traces,expected){
 const bars=traces.filter(t=>t.type==='bar'&&t.orientation==='h'&&t.y?.length===expected.length);
 assert.equal(bars.length,1,'A single full-roster probability chart is required');
 const t=bars[0],names=Array.from(t.y),values=Array.from(t.x);
 assert.equal(new Set(names).size,expected.length,'Duplicate displayed driver labels');
 for(const row of expected){
  const i=names.indexOf(row.name);assert(i>=0,'Driver absent from displayed chart: '+row.id);
  assert(Number.isFinite(values[i])&&Math.abs(values[i]-row.probability*100)<1e-10,'Displayed probability differs: '+row.id);
 }
 return expected.length;
}

async function verify(specPath,output){
 const spec=JSON.parse(fs.readFileSync(specPath,'utf8')),deadline=Date.parse(spec.race_start_utc);
 const runDeadline=Math.min(deadline,Date.now()+10*60*1000);
 assert(spec.rows.length===22&&new Set(spec.rows.map(r=>r.id)).size===22,'Full 22-driver roster required');
 assert(Date.now()<deadline,'Race has started; no late host acceptance');
 const base=process.env.PITWALL_PUBLIC_BASE_URL||'https://pitwall-lab.streamlit.app';
 const baseURL=new URL(base);assert(baseURL.protocol==='https:'||['localhost','127.0.0.1'].includes(baseURL.hostname));
 const engines=require(process.env.PLAYWRIGHT_MODULE||'playwright');
 output=path.resolve(output);fs.mkdirSync(output,{recursive:true});
 const report={schema:'pitwall-p1-served-forecast-v1',identity:spec.identity,pair_sha256:spec.pair_sha256,
  source_asset_sha256:spec.source_asset_sha256,version:spec.version,base,cases:[],status:'failed',
  automation_commit:spec.automation_commit,verifier_sha256:crypto.createHash('sha256').update(fs.readFileSync(__filename)).digest('hex')};
 const save=()=>fs.writeFileSync(path.join(output,'host-acceptance.json'),JSON.stringify(report,null,2)+'\n');
 try{
  for(const engine of ['chromium','webkit']){
   if(Date.now()>=runDeadline)break;
   const browser=await engines[engine].launch({headless:true});
   try{for(const width of [390,1440])for(const lang of ['pt','en']){
    const row={engine,width,lang,status:'failed',attempts:[]};report.cases.push(row);
    for(let attempt=1;attempt<=2;attempt++){
     if(Date.now()>=runDeadline){row.reason='acceptance_deadline_reached';break;}
     assert(Date.now()<deadline,'Race started during acceptance');
     const context=await browser.newContext({viewport:{width,height:1000},isMobile:width===390,hasTouch:width===390});
     const page=await context.newPage(),errors=[],capture={attempt,started_at_utc:new Date().toISOString()};
     page.on('pageerror',e=>errors.push(e.message));
     try{
      const query=new URLSearchParams({tela:'Previsões',temporada:String(spec.identity[0]),gp:String(spec.identity[1]),lang});
      await page.goto(base+'/?'+query,{waitUntil:'domcontentloaded',timeout:45000});
      const app=['localhost','127.0.0.1'].includes(baseURL.hostname)?page:page.frameLocator('iframe[src*="/~/+/"]').first();
      capture.controls=await ready(app,spec.version,lang);
      await app.locator('.st-key-fan-prediction-intro').waitFor({timeout:20000});
      const contextValues=await app.locator('.st-key-journey-context-row input').evaluateAll(nodes=>nodes.map(n=>n.value));
      assert(contextValues.some(v=>v===String(spec.identity[0]))&&contextValues.some(v=>v.startsWith(spec.identity[1]+' — ')),'Selected season/GP differs');
      const ids=await app.locator('.fan-probability-row').evaluateAll(nodes=>nodes.map(n=>new URL(n.href).searchParams.get('piloto')));
      assert.deepEqual([...ids].sort(),[...spec.favorites].sort(),'Displayed favorites differ from native forecast');
      const expander=app.locator('[data-testid=stExpander] summary').filter({hasText:lang==='pt'?'Chances de pódio por piloto':'Podium chances by driver'});
      await expander.click();
      await app.locator('.js-plotly-plot').waitFor({timeout:15000});
      const traces=await app.locator('.js-plotly-plot').evaluateAll(nodes=>nodes.flatMap(n=>(n.data||[]).map(t=>({type:t.type,orientation:t.orientation,x:Array.from(t.x||[]),y:Array.from(t.y||[])}))));
      row.rows_checked=checkPlot(traces,spec.rows);
      assert.equal(errors.length,0,'Browser page errors: '+errors.join('; '));
      assert(Date.now()<deadline,'Race started before observation completed');
      await page.screenshot({path:path.join(output,`${engine}-${width}-${lang}-${attempt}.jpg`),type:'jpeg',quality:75});
      assert.equal(errors.length,0,'Browser page errors during screenshot');
      capture.status='passed';row.status='passed';row.observed_at_utc=new Date().toISOString();
      break;
     }catch(error){capture.status='failed';capture.error=error.message;
      await page.screenshot({path:path.join(output,`${engine}-${width}-${lang}-${attempt}-failed.jpg`),type:'jpeg',quality:75,timeout:5000}).catch(()=>{});
     }finally{capture.page_errors=errors;row.attempts.push(capture);save();await context.close();}
    }
    save();console.log(JSON.stringify({engine,width,lang,status:row.status}));
   }}finally{await browser.close();}
  }
 }finally{
  report.completed_at_utc=new Date().toISOString();
  report.status=report.cases.length===8&&report.cases.every(c=>c.status==='passed')&&Date.now()<deadline?'passed':'failed';save();
 }
 assert.equal(report.status,'passed','Served forecast acceptance failed; attempts preserved');return report;
}
module.exports={checkPlot,verify};
if(require.main===module)verify(...process.argv.slice(2)).catch(e=>{console.error(e.message);process.exitCode=1;});
