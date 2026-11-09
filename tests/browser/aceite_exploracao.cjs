const {choose,reveal}=require('./sidebar_navigation.cjs');
const {selectComboboxOption}=require('./select_combobox.cjs');
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
 const frontendErrorsByPage = new WeakMap();
 async function stableIdle(page) {
  await page.waitForFunction(() => {
   if(document.querySelector('.stApp')?.getAttribute('data-test-script-state')!=='notRunning') {
    window.pitwallIdleSince=0;return false;
   }
   window.pitwallIdleSince ||= performance.now();
   return performance.now()-window.pitwallIdleSince>=1200;
  },null,{timeout:45000});
 }
 async function open(context, query, title) {
  const p = await context.newPage();
  const q=new URLSearchParams(query),route=q.get('tela'),en=q.get('lang')==='en';
  if(route==='Pilotos' && q.get('anos')) await p.addInitScript(() => {
   window.pitwallScopeHistory=[];
   new MutationObserver(() => {
    const text=document.querySelector('.fan-pilot-toolbar')?.textContent;
    if(text && window.pitwallScopeHistory.at(-1)!==text) window.pitwallScopeHistory.push(text);
   }).observe(document,{subtree:true,childList:true,characterData:true});
  });
  const frontendErrors = [];
  frontendErrorsByPage.set(p,frontendErrors);
  p.on('pageerror', error => frontendErrors.push(error.message));
  p.on('console', message => {
   if(message.type()==='error' && /Bad 'setIn'/.test(message.text())) frontendErrors.push(message.text());
  });
  await p.goto(base + '/?' + query);
  if(route==='Previsões') title=en?'Podium chances':'Chances de pódio';
  if(route==='Campeonato') title=(en?'Drivers championship':'Campeonato de pilotos');
  if(route==='Pilotos'&&!['perfil','duelo'].includes(q.get('visao'))) title=q.get('condicao')==='ccw'?(en?'Who stands out on anti-clockwise circuits?':'Quem se destaca no sentido anti-horário?'):(en?'Who stands out in the rain?':'Quem se destaca na chuva?');
  if(route==='Pilotos'&&q.get('visao')==='perfil') title='Lando Norris';
  if(route==='Pilotos'&&q.get('visao')==='duelo') title=en?'Head to head':'Duelo';

  try{await (route==='Corridas'||route==='Previsões'?p.locator('.pw-postcard h1'):p.getByRole('heading', {level:1, name:title, exact:true})).waitFor({timeout:45000});}catch(error){await p.screenshot({path:path.join(output,'failure.png')});throw Error(JSON.stringify({expected:title,url:p.url(),headings:await p.locator('h1').allTextContents(),exceptions:await p.locator('[data-testid=stException]').allTextContents(),frontendErrors}));}
  await p.waitForFunction(() => document.querySelector('.stApp')?.getAttribute('data-test-script-state') === 'notRunning');
  await stableIdle(p);
  await p.evaluate(async()=>{
   await document.fonts.ready;
   for(const icon of document.querySelectorAll('[data-testid="stIconMaterial"]')){const c=getComputedStyle(icon);await document.fonts.load(c.fontSize+' '+c.fontFamily,icon.textContent);}
   await document.fonts.ready;
  });
  check(frontendErrors.length===0,'Frontend rendering error: '+frontendErrors.join('; '));
  check(await p.locator('[data-testid="stException"]').count() === 0, 'Application exception');
  const hero=await p.locator('.fan-hero').boundingBox();
  const precedingSelector=q.get('visao')==='perfil'?'.st-key-pilot-profile-selector':route==='Pilotos'?'.st-key-pilot-view-navigation':
   route==='Previsões'&&await p.locator('.st-key-open_tarot').count()?'.st-key-open_tarot':'.st-key-journey-context-row';
  const preceding=await p.locator(precedingSelector).boundingBox();
  check(hero&&preceding&&hero.y>=preceding.y+preceding.height-1&&hero.y<preceding.y+preceding.height+70,'Cover overlaps or detaches from preceding navigation');
  check(await p.evaluate(()=>{
   const main=document.querySelector('.stMain').getBoundingClientRect(),dock=document.querySelector('.st-key-journey-navigation').getBoundingClientRect();
   return main.bottom<=innerHeight+1;
  }),'Main scrollport extends behind navigation');
  if(route==='Pilotos') {
   const scope=await p.locator('.fan-pilot-toolbar').boundingBox();
   const heading=await p.locator('.fan-hero h1').boundingBox();
   const filterControl=p.getByRole('button',{name:en?'Filters':'Filtros',exact:false});
   const filters=await filterControl.boundingBox();
   const subtitle=await p.locator('.fan-hero-copy>p').boundingBox();
   const chips=await p.locator('.fan-condition-chips').boundingBox();
   check(scope&&heading&&(scope.y+scope.height<=heading.y-4||scope.y>=heading.y+heading.height+4),'Driver criteria overlap the title');
   check(filters&&filters.x>=hero.x&&filters.x+filters.width<=hero.x+hero.width,'Driver filter button clipped');
   check(subtitle&&chips&&subtitle.y+subtitle.height<=chips.y-4,'Driver text overlaps condition controls');
   const chipTargets=await p.locator('.fan-condition-chips a').evaluateAll(items=>items.map(el=>{const r=el.getBoundingClientRect();return{width:r.width,height:r.height};}));
   check(chipTargets.length>0&&chipTargets.every(r=>r.width>=44&&r.height>=44),'Condition target smaller than44px');
   await filterControl.scrollIntoViewIfNeeded();
   check(await filterControl.evaluate(el=>{
    const r=el.getBoundingClientRect(),main=document.querySelector('.stMain').getBoundingClientRect(),hit=document.elementFromPoint((r.left+r.right)/2,(r.top+r.bottom)/2);
    return r.top>=main.top&&r.bottom<=main.bottom&&!!hit&&(hit===el||el.contains(hit));
   }),'Scrolled driver filter is covered or clipped');
   await p.locator('.stMain').evaluate(main=>main.scrollTo({top:0,behavior:'instant'}));
  }
  if(!['Corridas','Previsões'].includes(route))await p.locator('.fan-hero-image').evaluate(img=>img.decode());
  await stableIdle(p);
  await p.waitForFunction(()=>document.querySelectorAll('.st-key-pw-sidebar-menu button').length===15,null,{timeout:15000});
  check(await p.locator('.st-key-pw-sidebar-menu button').count()===15,'Sidebar: fifteen destinations required');

  return p;
 }
 let p;
 for(let attempt=0;attempt<5;attempt++){
 const context = await browser.newContext({viewport:{width:1440,height:1200}});
 p = await open(context, 'tela=Pilotos', 'Pilotos');
 await p.screenshot({path:path.join(output,'pilotos-pt.png')});
 // Resolve the iframe again after every rerender instead of retaining a detached Frame.
 let favourite = p.frameLocator('iframe[src*="pitwall_favorite"]').locator('select');
 await favourite.selectOption('max_verstappen');
 await p.getByRole('button',{name:'Ver meu favorito',exact:true}).waitFor();
 await p.reload();
 await p.locator('.fan-hero h1').waitFor();
 favourite = p.frameLocator('iframe[src*="pitwall_favorite"]').locator('select');
 await favourite.locator('option[value="max_verstappen"]:checked').waitFor({state:'attached',timeout:15000});
 // A persisted favourite must not overwrite a shared driver or period.
 p = await open(context, 'tela=Pilotos&visao=perfil&piloto=norris&anos=2026&lang=en', 'Drivers');
 await p.locator('.pilot-profile h2').filter({hasText:'Lando Norris'}).waitFor();
 check(await p.locator('iframe[src*="pitwall_favorite"]').count()===0,'Favourite control returned in the profile');
 await stableIdle(p);
 await p.waitForURL(url=>url.searchParams.get('anos')==='2026',{timeout:15000});
 await p.screenshot({path:path.join(output,`perfil-en-${attempt}.png`)});
 check(/History:\s*2026\b/.test(await p.locator('.fan-pilot-toolbar').innerText()),'Favourite rerun replaced shared period');
 const scopeHistory=await p.evaluate(()=>window.pitwallScopeHistory);
 check(scopeHistory.length>0 && scopeHistory.every(text=>(text.match(/\b20\d{2}\b/g)||[]).join(',')==='2026'),'Favourite temporarily replaced shared period: '+scopeHistory.join('; '));
 check(await p.locator('.pilot-profile h2').innerText()==='Lando Norris','Favourite rerun replaced shared driver');
 check(frontendErrorsByPage.get(p).length===0,'Late favourite rendering error: '+frontendErrorsByPage.get(p).join('; '));
 await selectComboboxOption(p,p.locator('.st-key-pilot-profile-selector').getByRole('combobox'),'Lewis Hamilton',{filter:true});
 await p.locator('.fan-hero h1').filter({hasText:'Lewis Hamilton'}).waitFor();
 await p.waitForURL(url=>url.searchParams.get('piloto')==='hamilton'&&url.searchParams.get('anos')==='2026');
 report.push({journey:'profile-selector-retains-scope',attempt,driver:'hamilton',period:'2026',scopeHistory});
 await context.close();
 }
 // A DeltaGenerator must never be shared between concurrent ScriptRunners.
 for(let round=0;round<3;round++){
  const parallel = await browser.newContext({viewport:{width:1440,height:1200}});
  const pages=await Promise.all([
   ['tela=Pilotos&visao=perfil&piloto=norris&anos=2026&lang=en','Lando Norris'],
   ['tela=Pilotos&visao=geral&lang=pt','Quem se destaca na chuva?'],
   ['tela=Metodologia&lang=en','How it works'],
  ].map(async([query,title],index)=>{
   const page=await open(parallel,query,title);
   await page.screenshot({path:path.join(output,`concurrent-${round}-${index}.png`)});
   return {title,headings:await page.locator('h1').allTextContents()};
  }));
  report.push({journey:'concurrent-session-headers',round,pages});
  await parallel.close();
 }
 const clean = await browser.newContext({viewport:{width:1440,height:1200}});
 p = await open(clean,'tela=Pilotos&visao=duelo&piloto=max_verstappen&rival=norris&anos=2026&metrica=win_rate&minimo=5&lang=en','Drivers');
 await p.getByRole('heading',{name:'Max Verstappen',exact:true}).waitFor();
 await p.getByRole('heading',{name:'Lando Norris',exact:true}).waitFor();
 await p.getByText('Share this analysis',{exact:true}).click();
 const url = await p.getByLabel('Shareable link',{exact:true}).inputValue();
 const query = new URL(url).searchParams;
 check(query.get('anos')==='2026' && query.get('piloto')==='max_verstappen' && query.get('rival')==='norris' && query.get('visao')==='duelo','Shared filters lost');
 report.push({journey:'duel-en',url,metrics:await p.locator('[data-testid="stMetric"]').allTextContents()});
 const driverMenu=()=>p.locator('.st-key-pilot-view-navigation').getByRole('button').filter({hasText:'Explore drivers'});
 check((await driverMenu().innerText()).includes('Explore drivers'),'Driver menu label must be English');
 await driverMenu().click();
 await p.getByText('Overview',{exact:true}).click();
 await p.getByRole('heading',{level:1,name:'Who stands out in the rain?',exact:true}).waitFor();
 await stableIdle(p);
 if(!await p.locator('[data-testid=stPopoverBody]').getByText('Head to head',{exact:true}).isVisible()) await driverMenu().click();
 await p.locator('[data-testid=stPopoverBody]').getByText('Head to head',{exact:true}).click();
 await p.getByRole('heading',{level:1,name:'Head to head',exact:true}).waitFor();
 await stableIdle(p);
 check(new URL(p.url()).searchParams.get('visao')==='duelo','Driver menu did not preserve its mode');
 check(new URL(p.url()).searchParams.get('anos')==='2026','Driver menu replaced shared period');
 check(new URL(p.url()).searchParams.get('piloto')==='max_verstappen' && new URL(p.url()).searchParams.get('rival')==='norris','Driver menu replaced a duel participant');
 report.push({journey:'driver-mode-menu-en',period:'2026',mode:'duelo'});
 p = await open(clean,'tela=Campeonato&temporada=2026&gp=18','Campeonato');
 const rows = await p.locator('.tabela-editorial tbody tr').count();
 check(rows > 25,'Championship truncated');
 report.push({journey:'championship',rows});
 p = await open(clean,'tela=Pilotos&lang=en','Drivers');
 await p.screenshot({path:path.join(output,'pilotos-en.png')});
 p = await open(clean,'tela=Corridas&temporada=2026&gp=18&lang=pt','United States Grand Prix');
 const desktopImage=await p.locator('.fan-hero').boundingBox();
 const desktopPodium=await p.getByRole('heading',{name:'Pódio da corrida',exact:true}).boundingBox();
 check(desktopImage && desktopPodium && desktopPodium.y>=desktopImage.y+desktopImage.height-45 && desktopPodium.y>desktopImage.y+desktopImage.height*.8,'Desktop circuit panel must precede podium');
 await p.screenshot({path:path.join(output,'resumo-desktop.png')});
 report.push({journey:'circuit-first-desktop',imageBottom:desktopImage.y+desktopImage.height,podiumTop:desktopPodium.y});
 p = await open(clean,'tela=Corridas&temporada=2026&gp=19&lang=en','Mexico City Grand Prix');
 await p.locator('summary').filter({hasText:'Updates and coverage'}).click();await p.getByText('Track incoming data',{exact:true}).waitFor();
 await choose(p,'weather');await p.locator('.pw-chapter h1').waitFor();
 check(await p.locator('[data-testid="stException"]').count()===0,'Mexico runtime error');
 await p.screenshot({path:path.join(output,'mexico-weather-en.png')});
 report.push({journey:'mexico-pending-en'});
 await clean.close();
 const journey=await browser.newContext({viewport:{width:1440,height:1100}});
 p=await open(journey,'tela=Corridas&temporada=2026&gp=18&lang=pt','United States Grand Prix');
 const dock=p.locator('.st-key-pw-sidebar-menu');
 check(await dock.locator('button').count()===15,'Missing sidebar destinations');
 await choose(p,'drivers-standing');
 await p.getByRole('heading',{name:'Campeonato de pilotos',level:1,exact:true}).waitFor();
 check(new URL(p.url()).searchParams.get('gp')==='18','Sidebar lost GP');
 await p.screenshot({path:path.join(output,'journey-championship.png')});
 p=await open(journey,'tela=Previsões&temporada=2026&gp=19&lang=pt','Mexico City Grand Prix');
 await reveal(p,'pt');
 check(await p.locator('.pw-tarot-prob').count()===3,'Missing recorded probabilities');
 await p.screenshot({path:path.join(output,'journey-cards.png')});
 report.push({journey:'sidebar-and-cards',cards:3,gp:19});
 await journey.close();
 const mobile = await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true,reducedMotion:'no-preference'});
 p = await open(mobile,'tela=Corridas&temporada=2026&gp=18','United States Grand Prix');
 const close = p.locator('[data-testid="stSidebarCollapseButton"] button');
 if(await close.isVisible()) await close.tap();
 await p.waitForTimeout(300);
 check(await p.locator('.journey-calendar:visible,.fan-gp-tabs:visible').count()===0,'Redundant GP navigation remains');
 check(await p.locator('.st-key-pw-sidebar-menu summary').isVisible(),'Mobile explorer must be reachable');
 check(!(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth)),'Mobile overflow');
 const imageTop=await p.locator('.fan-hero').first().boundingBox();
 const podiumTop=await p.getByRole('heading',{name:'Pódio da corrida',exact:true}).boundingBox();
 check(imageTop && podiumTop && podiumTop.y>=imageTop.y+imageTop.height-40 && podiumTop.y>imageTop.y+imageTop.height*.75,'Circuit image must precede podium');
 await p.screenshot({path:path.join(output,'corrida-mobile.png')});
 report.push({journey:'mobile',sidebar_destinations:await p.locator('.st-key-pw-sidebar-menu button').count()});
 const mobileMenu=p.locator('.st-key-pw-sidebar-menu details');await mobileMenu.locator('summary').click();
 for(const button of await p.locator('.st-key-pw-sidebar-menu button').all()){
  const box=await button.boundingBox();check(box&&box.width>=44&&box.height>=44&&box.x>=0&&box.x+box.width<=390,'Sidebar target clipped or too small');
 }
 await mobileMenu.locator('summary').click();
 for(const [route,title] of [['Pilotos','Pilotos'],['Campeonato','Campeonato'],['Previsões','United States Grand Prix'],['Desempenho','Acertos do Lab'],['Metodologia','Como funciona']]){
  p=await open(mobile,'tela='+encodeURIComponent(route)+'&temporada=2026&gp=18&lang=pt',title);
  check(!(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth)),'Page overflow: '+route);
  check(await p.locator('[data-testid="stException"]').count()===0,'Journey page exception: '+route);
  await p.screenshot({path:path.join(output,'journey-mobile-'+route+'.png')});
 }
 for(const lang of ['pt','en']) {
  p=await open(mobile,'tela=Pilotos&condicao=ccw&lang='+lang,'Drivers');
  await p.screenshot({path:path.join(output,'journey-mobile-ccw-'+lang+'.png')});
  report.push({journey:'mobile-long-condition-title',lang,condition:'ccw'});
 }
 p=await open(mobile,'tela=Previsões&temporada=2026&gp=19&lang=en','Mexico City Grand Prix');
 await reveal(p,'en');
 const deckGeometry=await p.locator('.pw-sealed-deck').evaluate(el=>({width:el.clientWidth,scrollWidth:el.scrollWidth,cards:[...el.querySelectorAll('.pw-revealed-face')].map(card=>({width:card.clientWidth,scrollWidth:card.scrollWidth,animations:card.getAnimations().map(a=>a.playState)}))}));
 fs.writeFileSync(path.join(output,'mobile-deck-geometry.json'),JSON.stringify(deckGeometry,null,2));
 check(deckGeometry.scrollWidth<=deckGeometry.width,'Mobile deck overflow: '+JSON.stringify(deckGeometry));
 await p.screenshot({path:path.join(output,'journey-mobile-cards-en.png')});
 report.push({journey:'mobile-all-pages-and-cards'});
 fs.writeFileSync(path.join(output,'evidence.json'),JSON.stringify(report,null,2));
 await browser.close();
 console.log(JSON.stringify({status:'passed',journeys:report}));
})().catch(e => {console.error(e);process.exit(1)});
