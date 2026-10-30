/* PT: Aceite das jornadas de fãs. EN: Fan journey acceptance. */
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const [base, output] = process.argv.slice(2);
if (!base || !output) throw Error('Usage: node aceite_exploracao.cjs URL OUTPUT');
const check = (value, message) => { if (!value) throw Error(message); };
const launch = {headless: true};
if (process.env.PLAYWRIGHT_CHANNEL) launch.channel = process.env.PLAYWRIGHT_CHANNEL;
fs.mkdirSync(output, {recursive:true});
(async () => {
 const browser = await chromium.launch(launch);
 const report = [];
 async function open(context, query, title) {
  const p = await context.newPage();
  await p.goto(base + '/?' + query);
  await p.getByRole('heading', {level:1, name:title, exact:true}).waitFor({timeout:30000});
  await p.waitForFunction(() => document.querySelector('.stApp')?.getAttribute('data-test-script-state') === 'notRunning');
  await p.waitForTimeout(700);
  check(await p.locator('[data-testid="stException"]').count() === 0, 'Application exception');
  return p;
 }
 const context = await browser.newContext({viewport:{width:1440,height:1200}});
 let p = await open(context, 'tela=Pilotos', 'Pilotos');
 await p.screenshot({path:path.join(output,'pilotos-pt.png')});
 let frame = p.frames().find(f => f.url().includes('pitwall_favorite'));
 check(frame, 'Missing favourite component');
 await frame.locator('select').selectOption('max_verstappen');
 await p.getByRole('button',{name:'Ver meu favorito',exact:true}).waitFor();
 await p.reload();
 await p.getByRole('heading',{level:1,name:'Pilotos',exact:true}).waitFor();
 frame = p.frames().find(f => f.url().includes('pitwall_favorite'));
 await frame.locator('select').waitFor();
 check(await frame.locator('select').inputValue() === 'max_verstappen', 'Favourite lost after reload');
 // A persisted favourite must not overwrite a shared driver or period.
 p = await open(context, 'tela=Pilotos&visao=perfil&piloto=norris&anos=2026&lang=en', 'Drivers');
 await p.locator('.pilot-profile h2').filter({hasText:'Lando Norris'}).waitFor();
 check(new URL(p.url()).searchParams.get('anos') === '2026', 'Profile period lost');
 await p.screenshot({path:path.join(output,'perfil-en.png')});
 await context.close();
 const clean = await browser.newContext({viewport:{width:1440,height:1200}});
 p = await open(clean,'tela=Pilotos&visao=duelo&piloto=max_verstappen&rival=norris&anos=2026&metrica=win_rate&minimo=5&lang=en','Drivers');
 await p.getByRole('heading',{name:'Max Verstappen',exact:true}).waitFor();
 await p.getByRole('heading',{name:'Lando Norris',exact:true}).waitFor();
 await p.getByText('Share this analysis',{exact:true}).click();
 const url = await p.getByLabel('Shareable link',{exact:true}).inputValue();
 const query = new URL(url).searchParams;
 check(query.get('anos')==='2026' && query.get('piloto')==='max_verstappen' && query.get('rival')==='norris' && query.get('visao')==='duelo','Shared filters lost');
 report.push({journey:'duel-en',url,metrics:await p.locator('[data-testid="stMetric"]').allTextContents()});
 p = await open(clean,'tela=Campeonato&temporada=2026&gp=18','Campeonato');
 const rows = await p.locator('.tabela-editorial tbody tr').count();
 check(rows > 25,'Championship truncated');
 report.push({journey:'championship',rows});
 p = await open(clean,'tela=Pilotos&lang=en','Drivers');
 await p.screenshot({path:path.join(output,'pilotos-en.png')});
 await clean.close();
 const mobile = await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
 p = await open(mobile,'tela=Corridas&temporada=2026&gp=18','United States Grand Prix');
 const close = p.locator('[data-testid="stSidebarCollapseButton"] button');
 if(await close.isVisible()) await close.tap();
 await p.waitForTimeout(300);
 for(const tab of await p.getByRole('tab').all()) { const r=await tab.boundingBox();check(r && r.x>=0 && r.x+r.width<=390,'Tab clipped'); }
 check(!(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth)),'Mobile overflow');
 await p.screenshot({path:path.join(output,'corrida-mobile.png')});
 report.push({journey:'mobile',tabs:await p.getByRole('tab').allTextContents()});
 fs.writeFileSync(path.join(output,'evidence.json'),JSON.stringify(report,null,2));
 await browser.close();
 console.log(JSON.stringify({status:'passed',journeys:report}));
})().catch(e => {console.error(e);process.exit(1)});
