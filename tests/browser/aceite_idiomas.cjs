/* PT/EN browser acceptance: node aceite_idiomas.cjs URL MANIFEST OUTPUT */
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const crypto = require('node:crypto');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const [url, manifestPath, output] = process.argv.slice(2);
const manifest = JSON.parse(fs.readFileSync(manifestPath));
const sha = value => crypto.createHash('sha256').update(value).digest('hex');
const expectedCsv = fs.readFileSync(path.join(path.dirname(manifestPath), 'reports/modelo_v1/previsoes_validacao.csv'));
const check = (ok, reason) => {if (!ok) throw Error(reason);};
fs.mkdirSync(output, {recursive:true});
const report = {build:manifest.apresentacao_build_sha256, version:manifest.versao_produto, url,
                public_verified:false, journeys:[], utc:new Date().toISOString()};
const server = http.createServer((req,res) => {
  const target=new URL(url);target.search=new URL(req.url,'http://localhost').search;
  res.setHeader('Content-Type','text/html; charset=utf-8');
  res.end(`<style>html,body{margin:0;width:100%;height:100%;overflow-x:hidden}iframe{width:100%;height:100vh;border:0}</style><iframe title="Dashboard" sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox allow-downloads" src="${target.href.replaceAll('&','&amp;')}"></iframe>`);
});
(async()=>{
  let browser;
  try {
    await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
    const shell=`http://127.0.0.1:${server.address().port}`;
    browser=await chromium.launch({channel:'chrome',headless:true});
    for(const viewport of [{width:1440,height:1000},{width:390,height:844}]) {
      const context=await browser.newContext({viewport,acceptDownloads:true});
      const page=await context.newPage();const errors=[];
      context.on('page', p=>p.on('pageerror',e=>errors.push(e.message)));
      page.on('pageerror',e=>errors.push(e.message));
      await page.goto(shell+'/?temporada=2026&gp=18&aba=Hist%C3%B3rico');
      let frame=page.frameLocator('iframe');
      await frame.getByText('Desempenho dos pilotos nesta pista',{exact:true}).waitFor({timeout:60000});
      await frame.getByRole('button',{name:'🇬🇧',exact:true}).click();
      await frame.getByText('Driver performance at this circuit',{exact:true}).waitFor({timeout:60000});
      const iframe=page.frames().find(f=>f.url().includes('lang=en'));
      check(!!iframe,'Language query was not retained');
      const state=new URL(iframe.url()).searchParams;
      check(state.get('gp')==='18' && state.get('temporada')==='2026' && state.get('aba')==='Histórico','Season, GP or tab lost on flag click');
      const flag=frame.getByRole('button',{name:'🇬🇧',exact:true});
      const box=await flag.boundingBox();const brBox=await frame.getByRole('button',{name:'🇧🇷',exact:true}).boundingBox();check(Math.abs(box.y-brBox.y)<5,'Flags stacked vertically');check(box && box.y>=0 && box.y+box.height<=125 && box.x>viewport.width-180 && box.x+box.width<=viewport.width,'Flags are not in the upper-right corner');
      const switches=frame.locator('[class*="st-key-pw_language_switch_"]:visible').first();
      const switchBox=await switches.boundingBox();
      const controls=await frame.locator('.st-key-topbar button:visible, .gp-cabecalho:visible').all();
      for(const control of controls){const rect=await control.boundingBox();if(rect)check(!(switchBox.x<rect.x+rect.width && switchBox.x+switchBox.width>rect.x && switchBox.y<rect.y+rect.height && switchBox.y+switchBox.height>rect.y),'Language switch overlaps header controls');}
      const csvPromise=page.waitForEvent('download');
      await frame.getByRole('button',{name:'Download table CSV',exact:true}).first().click();
      const csv=await csvPromise;const destination=path.join(output,`history-en-${viewport.width}.csv`);await csv.saveAs(destination);
      const bytes=fs.readFileSync(destination).toString('utf8');
      check(bytes.includes('Driver,Participations,Wins,Podiums') && bytes.includes('Max Verstappen'),'Descriptive CSV is not English');
      check(!bytes.includes('Pontos observados'),'Portuguese heading leaked into English CSV');
      await frame.locator('[data-testid="stApp"][data-test-script-state="notRunning"]').waitFor({timeout:60000});
      await page.waitForTimeout(300);
      await page.screenshot({path:path.join(output,`history-en-${viewport.width}.png`)});
      await frame.getByRole('tab',{name:'Overview',exact:true}).click();
      const drivers=frame.locator('table[aria-label="Drivers\' championship"]');
      await drivers.waitFor();check(await drivers.locator('tbody tr').count()===23,'Incomplete English standings');
      await frame.getByText('Not applicable in 2026',{exact:true}).waitFor();
      await frame.locator('[data-testid="stApp"][data-test-script-state="notRunning"]').waitFor({timeout:60000});
      await page.waitForTimeout(300);await page.screenshot({path:path.join(output,`overview-en-${viewport.width}.png`)});
      const popupPromise=context.waitForEvent('page');
      await frame.getByRole('link',{name:'View predictions for this GP',exact:true}).click();
      const prediction=await popupPromise;
      await prediction.getByText('Favourites by published ranking',{exact:true}).waitFor({timeout:60000});
      check(new URL(prediction.url()).searchParams.get('lang')==='en','Prediction link lost language');
      await page.goto(shell+'/?temporada=2026&gp=18&tela=Metodologia&lang=en');frame=page.frameLocator('iframe');
      await frame.getByText(`Interface build: ${manifest.apresentacao_build_sha256}`,{exact:true}).waitFor({timeout:60000});
      const docPromise=context.waitForEvent('page');await frame.getByRole('link',{name:'2024 report',exact:true}).click();
      const doc=await docPromise;
      await doc.getByRole('heading',{name:'Stage 4 — v1 podium-probability model',exact:true}).waitFor({timeout:60000});
      check(new URL(doc.url()).searchParams.get('lang')==='en','Document link lost language');
      const downloadPromise=doc.waitForEvent('download');await doc.getByRole('button',{name:'Download 2024 predictions (CSV)',exact:true}).click();
      const download=await downloadPromise;const scientific=path.join(output,`scientific-${viewport.width}.csv`);await download.saveAs(scientific);
      check(sha(fs.readFileSync(scientific))===sha(expectedCsv),'Scientific CSV changed during translation');
      await frame.getByRole('button',{name:'🇧🇷',exact:true}).click();
      await frame.getByText('Método histórico',{exact:true}).waitFor({timeout:60000});
      const portuguese=page.frames().find(f=>f.url().includes('lang=pt'));
      check(new URL(portuguese.url()).searchParams.get('gp')==='18','Return to Portuguese lost GP');
      check(errors.length===0,'Browser errors: '+errors.join('; '));
      report.journeys.push({viewport,flags:'clicked_both',gp_season_tab:'retained',english_views:'verified',
        descriptive_csv:'english',scientific_csv:'byte_identical',documents:'english',build:'matched',errors});
      await context.close();
    }
    report.result='passed_local_iframe';
  } catch(e) {report.result='failed';report.error=e.message;process.exitCode=1;}
  finally {fs.writeFileSync(path.join(output,'acceptance.json'),JSON.stringify(report,null,2));if(browser)await browser.close();server.close();}
})();
