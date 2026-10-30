/* PT: verifica o app servido; EN: checks the served deployment. */
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs');
const [version,resultPath]=process.argv.slice(2);
if(!/^\d+\.\d+\.\d+$/.test(version||''))throw Error('Expected semantic version');
const result=JSON.parse(fs.readFileSync(resultPath,'utf8'));
const round=result.identidade[1];
(async()=>{
 const browser=await chromium.launch({headless:true});
 let last;
 try {
  for(let attempt=0;attempt<4;attempt++){
   const context=await browser.newContext();
   try {
    const page=await context.newPage();
    await page.goto(`https://pitwall-lab.streamlit.app/?tela=Corridas&temporada=2026&gp=${round}&lang=en`,{waitUntil:'domcontentloaded',timeout:45000});
    let app;
    for(let n=0;n<30;n++){
     app=page.frames().find(f=>f.url().includes('/~/+/'));
     if(app)break;
     await page.waitForTimeout(500);
    }
    if(!app)throw Error('Public app frame unavailable');
    await app.getByText('v'+version,{exact:true}).first().waitFor({timeout:45000});
    await app.getByText('Track incoming data',{exact:true}).waitFor({timeout:15000});
    await app.waitForFunction(()=>document.querySelector('.stApp')?.getAttribute('data-test-script-state')==='notRunning');
    if(await app.locator('[data-testid="stException"]').count())throw Error('Public application exception');
    console.log(JSON.stringify({publicVersion:version,round,verified:true,utc:new Date().toISOString()}));
    return;
   }catch(error){last=error;}
   finally{await context.close();}
   await new Promise(resolve=>setTimeout(resolve,10000));
  }
  throw last;
 }finally{await browser.close();}
})().catch(error=>{console.error(error.message);process.exit(1)});
