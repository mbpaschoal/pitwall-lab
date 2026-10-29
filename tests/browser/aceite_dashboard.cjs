/* Uso: PLAYWRIGHT_MODULE=/caminho/playwright node aceite_dashboard.cjs URL MANIFESTO EVIDENCIAS */
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const crypto = require('node:crypto');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const [baseUrl, manifestPath, outputDir] = process.argv.slice(2);
if (!baseUrl || !manifestPath || !outputDir) throw Error('Informe URL, MANIFESTO.json e diretório de evidências');
const manifest = JSON.parse(fs.readFileSync(manifestPath));
const build = manifest.apresentacao_build_sha256;
const expectedCsv = fs.readFileSync(path.join(path.dirname(manifestPath), 'reports/modelo_v1/previsoes_validacao.csv'));
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const check = (value, message) => { if (!value) throw Error(message); };
fs.mkdirSync(outputDir, {recursive: true});
const report = {url: baseUrl, build_esperado: build, ambiente: 'local_iframe_simulado',
                publicado_verificado: false, verificado_em_utc: new Date().toISOString(), jornadas: []};
const shell = http.createServer((req, res) => {
  const target = new URL(baseUrl); target.search = new URL(req.url, 'http://localhost').search;
  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  const url = target.href.replaceAll('&', '&amp;').replaceAll('"', '&quot;');
  res.end(`<style>html,body{margin:0;width:100%;height:100%;overflow-x:hidden}iframe{border:0;width:100%;height:100vh}</style><iframe title="Dashboard" sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox allow-downloads" src="${url}"></iframe>`);
});
(async () => {
  let browser;
  try {
    await new Promise(resolve => shell.listen(0, '127.0.0.1', resolve));
    const origin = `http://127.0.0.1:${shell.address().port}`;
    browser = await chromium.launch({channel: 'chrome', headless: true});
    for (const viewport of [{width: 1440, height: 1000}, {width: 390, height: 844}]) {
      const context = await browser.newContext({viewport, acceptDownloads: true});
      const page = await context.newPage();
      const errors = [];
      context.on('page', p => p.on('pageerror', e => errors.push(e.message)));
      page.on('pageerror', e => errors.push(e.message));
      await page.goto(origin + '/?temporada=2026&gp=18');
      let frame = page.frameLocator('iframe');
      const pilots = frame.locator('table[aria-label="Campeonato de pilotos"]');
      await pilots.waitFor({timeout: 60000});
      const teams = frame.locator('table[aria-label="Campeonato de construtores"]');
      check(await pilots.count() === 1 && await teams.count() === 1, 'Campeonato duplicado/ausente');
      check(await pilots.locator('tbody tr').count() === 23, 'Campeonato de pilotos incompleto');
      check(await teams.locator('tbody tr').count() === 11, 'Campeonato de equipes incompleto');
      const dashboardFrame = page.frames().find(f => f.url().startsWith(baseUrl));
      const overflow = await dashboardFrame.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
      check(!overflow, 'Overflow horizontal');
      await page.screenshot({path: path.join(outputDir, `corridas-${viewport.width}.png`)});
      await frame.getByText('Altitude aprox.', {exact: true}).waitFor();
      await frame.getByText('Não se aplica em 2026', {exact: true}).waitFor();
      await frame.getByRole('tab', {name: 'Histórico', exact: true}).click();
      await frame.getByText('Desempenho dos pilotos nesta pista', {exact: true}).waitFor();
      await frame.getByText('5 edições anteriores, de 2021 a 2025. A corrida selecionada está excluída.', {exact: true}).waitFor();
      // A aba oculta precisa concluir o ResizeObserver do canvas antes da captura.
      await page.waitForTimeout(600);
      await page.screenshot({path: path.join(outputDir, `historico-${viewport.width}.png`)});
      await frame.getByRole('tab', {name: 'Visão geral', exact: true}).click();
      const popupPromise = context.waitForEvent('page', {timeout: 20000});
      await frame.locator('a[href*="tela=Previs"]').first().click();
      const predictions = await popupPromise;
      await predictions.getByText('Favoritos por ranking publicado', {exact: true}).waitFor({timeout: 60000});
      const target = new URL(predictions.url());
      check(target.searchParams.get('temporada') === '2026' && target.searchParams.get('gp') === '18', 'Identidade perdida no clique');
      check(await predictions.locator('table[aria-label="Campeonato de pilotos"]').count() === 0, 'Campeonato repetido em Previsões');
      await page.goto(origin + '/?temporada=2026&gp=18&tela=Metodologia');
      frame = page.frameLocator('iframe');
      await frame.getByText(`Versão da interface: ${build}`, {exact: true}).waitFor({timeout: 60000});
      const documentPromise = context.waitForEvent('page', {timeout: 20000});
      await frame.getByRole('link', {name: 'Relatório de 2024', exact: true}).click();
      const doc = await documentPromise;
      const button = doc.getByRole('button', {name: 'Baixar previsões de 2024 (CSV)', exact: true});
      await button.waitFor({timeout: 60000});
      const downloadPromise = doc.waitForEvent('download');
      await button.click();
      const download = await downloadPromise;
      const csvPath = path.join(outputDir, `previsoes-${viewport.width}.csv`);
      await download.saveAs(csvPath);
      check(sha(fs.readFileSync(csvPath)) === sha(expectedCsv), 'CSV baixado diverge do pacote');
      check(errors.length === 0, 'Erros de página: ' + errors.join('; '));
      report.jornadas.push({viewport, campeonatos: [23, 11], clique_previsoes: 'aprovado',
                            historico_pista: 'cinco_edicoes_anteriores', ficha_circuito: 'aprovada', documento_csv: 'aprovado', build: 'conferido', overflow: false, erros: errors});
      await context.close();
    }
    report.resultado = 'aprovado_local_iframe';
  } catch (error) {
    report.resultado = 'falhou'; report.erro = error.message; process.exitCode = 1;
  } finally {
    fs.writeFileSync(path.join(outputDir, 'navegador.json'), JSON.stringify(report, null, 2));
    if (browser) await browser.close();
    shell.close();
    console.log(JSON.stringify(report));
  }
})();
