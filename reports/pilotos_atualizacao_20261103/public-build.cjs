/* PT/EN: build served in a fresh hosted-app context, allowing one bootstrap reload. */
const fs=require('node:fs'),path=require('node:path');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const [root,out]=process.argv.slice(2),m=JSON.parse(fs.readFileSync(path.join(root,'distribuicao/pitwall-dashboard/MANIFESTO.json')));
(async()=>{fs.mkdirSync(out,{recursive:true});const b=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHANNEL?{channel:process.env.PLAYWRIGHT_CHANNEL}:{})});try{
 const ctx=await b.newContext({viewport:{width:1440,height:1100}}),p=await ctx.newPage();
 await p.goto('https://pitwall-lab.streamlit.app/?tela=Metodologia&temporada=2026&gp=19&lang=en',{waitUntil:'domcontentloaded',timeout:60000});
 const app=p.frameLocator('iframe[src*="/~/+/"]').first();let reloads=0;
 for(let i=0;i<2;i++){try{await app.getByText('v'+m.versao_produto,{exact:true}).first().waitFor({timeout:60000});await app.locator('.fan-hero h1').waitFor({timeout:60000});break;}catch(e){if(i)throw e;reloads++;await p.reload({waitUntil:'domcontentloaded',timeout:60000});}}
 const more=app.locator('summary').filter({hasText:'For a closer look'});await more.click();
 await app.getByText('Interface build: '+m.apresentacao_build_sha256,{exact:true}).waitFor({timeout:45000});
 if(await app.locator('[data-testid="stException"]').count())throw Error('App exception');
 await p.screenshot({path:path.join(out,'public-build.png'),fullPage:true});
 const v={publicVersion:m.versao_produto,build:m.apresentacao_build_sha256,verified:true,reloads,utc:new Date().toISOString(),freshBrowserContext:true,url:p.url()};
 fs.writeFileSync(path.join(out,'public-build.json'),JSON.stringify(v,null,2)+'\n');console.log(JSON.stringify(v));await ctx.close();
 }finally{await b.close();}})().catch(e=>{console.error(e);process.exit(1)});
