/* Read-only served-build proof; this does not certify data collection or exports. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const out=process.argv[2];assert(out);fs.mkdirSync(out,{recursive:true});
const expected='d0b2abe139e1295b4dd8516558ef4d928bb4d7de9ea237766a03a8017b1f4a53';
const report={version:'0.8.27',expected_build:expected,cases:[]};
(async()=>{const browser=await chromium.launch({headless:true,channel:'chrome'});try{
for(const width of [1440,390])for(const lang of ['pt','en']){
 const context=await browser.newContext({viewport:{width,height:1000},isMobile:width===390,hasTouch:width===390});
 const page=await context.newPage(),network=[],errors=[];const row={width,lang,attempts:[]};
 page.on('requestfailed',r=>network.push({path:new URL(r.url()).pathname,error:r.failure()?.errorText}));
 page.on('pageerror',e=>errors.push(e.message));
 try{
  const url='https://pitwall-lab.streamlit.app/?'+new URLSearchParams({tela:'Metodologia',temporada:'2026',gp:'20',lang});
  const app=page.frameLocator('iframe[src*="/~/+/"]').first();
  let loaded=false;
  for(let attempt=0;attempt<2;attempt++){
   try{
    await page.goto(url,{waitUntil:'domcontentloaded',timeout:60000});
    await app.getByText('v0.8.27',{exact:true}).first().waitFor({timeout:60000});
    await app.locator('.fan-hero h1').waitFor({timeout:30000});
    await app.locator('.stApp[data-test-script-state="notRunning"]').waitFor({timeout:30000});
    await app.locator('[data-testid=stExpander] summary').filter({hasText:lang==='pt'?'Para quem quer ir além':'For a closer look'}).click();
    await app.getByText(expected,{exact:false}).first().waitFor({timeout:15000});
    const language=await app.locator('html').getAttribute('lang');assert.equal(language,lang);
    assert.equal(await app.locator('[data-testid=stException]').count(),0);
    assert.equal(await app.locator('body').evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
    row.attempts.push({attempt,status:'passed',utc:new Date().toISOString()});loaded=true;break;
   }catch(e){row.attempts.push({attempt,status:'failed',error:e.message,utc:new Date().toISOString()});}
  }
  assert(loaded,'Served build was not verified');row.status='passed';row.observed_build=expected;
 }catch(e){row.status='failed';row.error=e.message;}
 finally{
  row.network_failures=network;row.page_errors=errors;row.utc=new Date().toISOString();
  await page.screenshot({path:path.join(out,`${width}-${lang}-${row.status}.png`)}).catch(()=>{});
  report.cases.push(row);fs.writeFileSync(path.join(out,'build.json'),JSON.stringify(report,null,2));await context.close();
 }
}
}finally{await browser.close();}assert(report.cases.every(c=>c.status==='passed'),'Some public cases failed');
})().catch(e=>{console.error(e);process.exitCode=1;});
