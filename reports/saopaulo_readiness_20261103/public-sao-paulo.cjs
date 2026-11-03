/* PT/EN: future São Paulo must never borrow Mexico's forecast or tarot cards. */
const fs=require('node:fs'),path=require('node:path');
const {chromium,devices}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const [baseArg,output]=process.argv.slice(2);
const base=(baseArg||'').replace(/\/+$/,'');
if(!base||!output)throw Error('Usage: public-sao-paulo.cjs URL OUTPUT');
const version=fs.readFileSync(path.join(__dirname,'../../VERSION'),'utf8').trim();
const check=(ok,message)=>{if(!ok)throw Error(message);};
fs.mkdirSync(output,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true,channel:process.env.PLAYWRIGHT_CHANNEL||'chrome'}),cases=[];
 try{for(const mobile of (process.env.PITWALL_MOBILE_ONLY==='1'?[true]:[false,true]))for(const lang of ['pt','en']){
  const context=await browser.newContext(mobile?{...devices['Pixel 7'],viewport:{width:390,height:844}}:{viewport:{width:1440,height:1100}});
  const page=await context.newPage(),key=(mobile?'mobile':'desktop')+'-'+lang;
  let bootstrapReloads=0;
  try{
   async function open(route,gp){
    await page.goto(base+'/?'+new URLSearchParams({tela:route,temporada:'2026',gp:String(gp),lang}),{waitUntil:'domcontentloaded',timeout:60000});
    for(let attempt=0;attempt<2;attempt++){
     const app=page.frameLocator('iframe[src*="/~/+/"]').first();
     try{
      await app.getByText('v'+version,{exact:true}).first().waitFor({timeout:60000});
      await app.locator('.fan-hero h1').waitFor({timeout:60000});
      await app.locator('.stApp[data-test-script-state="notRunning"]').waitFor({timeout:60000});
      check(await app.locator('[data-testid="stException"]').count()===0,'Application exception');
      return app;
     }catch(error){
      if(attempt===1)throw error;
      bootstrapReloads++;
      await page.screenshot({path:path.join(output,key+'-'+gp+'-bootstrap-retry.png')});
      console.log(key+' reloading host bootstrap');
      await page.reload({waitUntil:'domcontentloaded',timeout:60000});
     }
    }
   }
   let app=await open('Previsões',20);
   check(await app.locator('.fan-probability-row').count()===0,'Future GP borrowed probabilities');
   check(await app.locator('.st-key-open_tarot').count()===0,'Future GP exposes forecast tarot');
   const pending=await app.locator('.fan-forecast-note').allTextContents();
   check(pending.length>0,'Missing explicit forecast-pending message');
   await page.screenshot({path:path.join(output,key+'-sao-paulo-pending.png')});
   app=await open('Corridas',20);
   check((await app.locator('.fan-hero h1').innerText()).includes('Brazilian'),'Wrong selected GP');
   check(await app.locator('.fan-podium-place').count()===0,'Future GP borrowed race podium');
   app=await open('Previsões',19);
   check(await app.locator('.fan-probability-row').count()>=3,'Mexico forecast disappeared');
   check(await app.locator('.st-key-open_tarot').count()===1,'Mexico optional tarot disappeared');
   cases.push({lang,mobile,status:'passed',version,bootstrapReloads,device:mobile?'Pixel 7':'desktop',future_gp:20,pending,forecast_borrowed:false,mexico_preserved:true});
   fs.writeFileSync(path.join(output,'acceptance.json'),JSON.stringify({status:'passed',cases},null,2)+'\n');
   console.log(key+' passed');
  }catch(e){await page.screenshot({path:path.join(output,key+'-failure.png')});throw e;}
  finally{await context.close();}
 }}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
