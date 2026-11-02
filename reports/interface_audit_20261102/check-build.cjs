const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs'),path=require('node:path');
const root=process.env.PITWALL_SOURCE_ROOT||require('node:path').resolve(__dirname,'../..');
const manifest=JSON.parse(fs.readFileSync(path.join(root,'distribuicao/pitwall-dashboard/MANIFESTO.json')));
const record={utc:new Date().toISOString(),expectedVersion:manifest.versao_produto,expectedBuild:manifest.apresentacao_build_sha256,url:'https://pitwall-lab.streamlit.app/'};
(async()=>{const browser=await chromium.launch({channel:'chrome',headless:true});
try{const context=await browser.newContext({viewport:{width:1040,height:992}}),page=await context.newPage();
await page.goto(record.url+'?tela=Metodologia&temporada=2026&gp=18&lang=en',{waitUntil:'domcontentloaded',timeout:60000});
let app;
for(let i=0;i<40;i++){app=page.frames().find(f=>f.url().includes('/~/+/'));if(app)break;await page.waitForTimeout(500);}
if(!app)throw Error('Public app iframe not found');
record.appUrl=app.url();
await app.locator('.fan-hero').waitFor({timeout:45000});
await app.locator('[data-testid="stApp"][data-test-script-state="notRunning"]').waitFor({timeout:45000});
record.version=(await app.locator('body').innerText()).match(/v0\.\d+\.\d+/)?.[0];
if(record.version!=='v'+manifest.versao_produto){record.status='awaiting_deploy';return;}
await app.locator('summary').filter({hasText:'For a closer look'}).click();
await app.getByText('Interface build: '+manifest.apresentacao_build_sha256,{exact:true}).waitFor({timeout:30000});
record.build=manifest.apresentacao_build_sha256;
record.lang=await app.evaluate(()=>document.documentElement.lang);
record.exceptions=await app.locator('[data-testid="stException"]').allTextContents();
if(record.exceptions.length)throw Error('Streamlit exception');
record.status='expected_version_and_build_served';
await page.screenshot({path:path.join(__dirname,'build-served.jpg'),scale:'css',type:'jpeg',quality:75});
}catch(error){record.status='check_error';record.error=error.message;}
finally{await browser.close();fs.writeFileSync(path.join(__dirname,'deploy-check.json'),JSON.stringify(record,null,2));console.log(JSON.stringify(record));}
})();
