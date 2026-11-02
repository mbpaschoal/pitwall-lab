/* PT/EN: independent live build receipt / recibo independente do build servido. */
const fs=require('node:fs');
const path=require('node:path');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const [root,out]=process.argv.slice(2);
const manifest=JSON.parse(fs.readFileSync(path.join(root,'distribuicao/pitwall-dashboard/MANIFESTO.json'),'utf8'));
const version=manifest.versao_produto;
const build=manifest.apresentacao_build_sha256;
if(!/^\d+\.\d+\.\d+$/.test(version)||!/^[a-f0-9]{64}$/.test(build))throw Error('Invalid expected identity');
(async()=>{
 fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({channel:process.env.PLAYWRIGHT_CHANNEL||'chrome',headless:true});
 try{
  const context=await browser.newContext({viewport:{width:1440,height:1100}});
  const page=await context.newPage();
  await page.goto('https://pitwall-lab.streamlit.app/?tela=Metodologia&temporada=2026&gp=19&lang=en',{waitUntil:'domcontentloaded',timeout:45000});
  let app;
  for(let n=0;n<90;n++){
   app=page.frames().find(f=>f.url().includes('/~/+/'));
   if(app)break;
   await page.waitForTimeout(500);
  }
  if(!app)throw Error('Public iframe unavailable');
  await app.getByText('v'+version,{exact:true}).first().waitFor({timeout:90000});
  await app.locator('summary').filter({hasText:'For a closer look'}).click();
  await app.getByText('Interface build: '+build,{exact:true}).waitFor({timeout:45000});
  await app.waitForFunction(()=>document.querySelector('.stApp')?.getAttribute('data-test-script-state')==='notRunning');
  if(await app.locator('[data-testid="stException"]').count())throw Error('Public application exception');
  await page.screenshot({path:path.join(out,'public-build.png'),fullPage:true});
  const result={publicVersion:version,build,verified:true,utc:new Date().toISOString(),url:page.url(),freshBrowserContext:true};
  fs.writeFileSync(path.join(out,'public-build.json'),JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify(result));
  await context.close();
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
