/* PT/EN: metric differences, shared cohorts, responsive portraits and motion. */
const fs = require('node:fs'), path = require('node:path'), assert = require('node:assert/strict');
const pw = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const [base, output] = process.argv.slice(2);
assert(base && output, 'Usage: aceite_editorial.cjs URL OUTPUT');
const engine = process.env.PLAYWRIGHT_BROWSER || 'chromium';
const root = process.env.PITWALL_SOURCE_ROOT || path.resolve(__dirname, '../..');
const read = name => JSON.parse(fs.readFileSync(path.join(root, name), 'utf8'));
const version = fs.readFileSync(path.join(root, 'VERSION'), 'utf8').trim();
const baseline = read('frontend_assets/pilotos_condicoes.json');
const supplement = read('frontend_assets/pilotos_condicoes_operacao.json');
const events = Object.values(supplement.events);
const gps = {...baseline.gps, ...Object.fromEntries(events.map(x => [x.gp.temporada + ':' + x.gp.rodada, x.gp]))};
const rows = [...new Map(baseline.resultados.concat(...events.map(x => x.results)).map(x => [x.race_id + ':' + x.driver_id, x])).values()];
const english = read('pitwall/i18n/en.json');
fs.mkdirSync(output, {recursive: true});
const report = {version, engine, base, cases: []};
function oracle(condition, metric) {
  const eligible = row => row.started && gps[row.race_id].temporada === 2026 &&
    (condition === 'all' || condition === 'rain' && gps[row.race_id].rain_condition === 'recorded');
  const left = new Map(rows.filter(x => eligible(x) && x.driver_id === 'max_verstappen').map(x => [x.race_id, x]));
  const common = rows.filter(x => eligible(x) && x.driver_id === 'norris' && left.has(x.race_id));
  const count = (sample, position) => sample.filter(x => !x.disqualified && x.position !== null && x.position <= position).length;
  const values = [common.map(x => left.get(x.race_id)), common].map(sample => {
    const n = count(sample, metric.startsWith('win') ? 1 : 3);
    return metric.endsWith('rate') ? (sample.length ? n / sample.length : null) : n;
  });
  return {n: common.length, values, comparable: common.filter(x => !x.disqualified && x.position !== null && !left.get(x.race_id).disqualified && left.get(x.race_id).position !== null).length};
}
async function surface(page) {
  if (!base.includes('streamlit.app')) return page;
  for (let i = 0; i < 120; i++) {
    const frame = page.frames().find(f => f.url().includes('/~/+/'));
    if (frame) return frame;
    await page.waitForTimeout(250);
  }
  throw Error('Public app frame missing');
}
async function ready(page, lang, expected = {}) {
  const app = await surface(page);
  await app.waitForFunction(({lang, version, expected}) => {
    const q = new URL(location.href).searchParams;
    return document.documentElement.lang === lang && document.querySelector('.stApp')?.dataset.testScriptState === 'notRunning' &&
      document.querySelector('.st-key-journey-header')?.innerText.includes('v' + version) &&
      Object.entries(expected).every(([key, value]) => q.get(key) === String(value));
  }, {lang, version, expected}, {timeout: 90000});
  await app.evaluate(() => document.fonts.ready);
  assert.equal(await app.locator('[data-testid=stException]').count(), 0);
  assert(!await app.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), 'Horizontal overflow');
  return app;
}
async function select(app, key, name) {
  const control = app.locator('.st-key-' + key).getByRole('combobox');
  await control.scrollIntoViewIfNeeded(); await control.click();
  await app.getByRole('option', {name, exact: true}).click();
}
(async () => {
  const launch = {headless: true};
  if (engine === 'chromium' && process.env.PLAYWRIGHT_CHANNEL) launch.channel = process.env.PLAYWRIGHT_CHANNEL;
  const browser = await pw[engine].launch(launch);
  try {
    for (const width of [1440, 390]) for (const lang of ['pt', 'en']) {
      const context = await browser.newContext({viewport: {width, height: 1000}, isMobile: width === 390, hasTouch: width === 390});
      const page = await context.newPage(), row = {width, lang, checks: []}, errors = [];
      const tr = text => lang === 'en' ? (english[text] || text) : text;
      page.on('pageerror', error => errors.push(error.message));
      async function open(extra = {}) {
        await page.goto(base + '/?' + new URLSearchParams({tela: 'Pilotos', visao: 'duelo', piloto: 'max_verstappen', rival: 'norris', anos: '2026', temporada: '2026', gp: '19', minimo: '5', metrica: 'win_rate', lang, ...extra}), {waitUntil: 'domcontentloaded', timeout: 90000});
        return ready(page, lang, {visao: 'duelo', ...extra});
      }
      async function compare(app, condition, metric, minimum) {
        const expected = oracle(condition, metric), difference = app.locator('.fan-duel-difference');
        const state = expected.n < minimum ? 'insufficient' : Math.abs(expected.values[0] - expected.values[1]) < 1e-12 ? 'tied' : expected.values[0] > expected.values[1] ? 'left' : 'right';
        await app.waitForFunction(({metric, state}) => {
          const e = document.querySelector('.fan-duel-difference');
          return e?.dataset.metric === metric && e?.dataset.state === state;
        }, {metric, state}, {timeout: 30000});
        const text = await difference.innerText();
        if (state !== 'insufficient' && state !== 'tied') {
          const amount = Math.abs(expected.values[0] - expected.values[1]) * (metric.endsWith('rate') ? 100 : 1);
          const formatted = metric.endsWith('rate') ? amount.toFixed(1).replace('.', lang === 'pt' ? ',' : '.') : String(amount);
          assert(text.includes(formatted), 'Difference does not match the independently counted source cohort');
          if (metric.endsWith('rate')) assert(text.includes(tr('pontos percentuais')));
        }
        const caption = app.locator('[data-testid=stCaptionContainer]').filter({hasText: new RegExp(expected.n + ' (largadas em comum|shared starts)')}).first();
        await caption.waitFor(); assert((await caption.innerText()).includes(String(expected.comparable)));
        row.checks.push({condition, metric, minimum, ...expected, state, text});
      }
      try {
        let app = await open();
        await compare(app, 'all', 'win_rate', 5);
        const driverHeaders = app.locator('.fan-duel-driver');
        assert.equal(await driverHeaders.count(), 2);
        for (const header of await driverHeaders.all()) await header.locator('img').evaluate(img => img.decode());
        const boxes = await driverHeaders.evaluateAll(items => items.map(e => {const r = e.getBoundingClientRect(); return {x: r.x, y: r.y, right: r.right, height: r.height};}));
        assert(Math.abs(boxes[0].y - boxes[1].y) < 1.5 && boxes[0].right < boxes[1].x, 'Portraits must share a row without overlap');
        await app.locator('.st-key-duel-stage').scrollIntoViewIfNeeded();
        await page.screenshot({path: path.join(output, `${width}-${lang}-duel.jpg`), type: 'jpeg', quality: 80});
        if (width === 390) {
          // A narrow viewport and larger user text must reflow the comparison.
          await page.setViewportSize({width: 320, height: 1000});
          await app.evaluate(() => document.documentElement.style.fontSize = '200%');
          const reflow = await driverHeaders.evaluateAll(items => items.map(e => {const r = e.getBoundingClientRect(); return {x: r.x, y: r.y, bottom: r.bottom};}));
          assert(reflow[1].y >= reflow[0].bottom && Math.abs(reflow[0].x - reflow[1].x) < 1.5, 'Larger text in a narrow viewport must stack the driver panels');
          assert(!await app.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), 'Larger text must not overflow');
          await app.locator('.fan-duel-driver').first().scrollIntoViewIfNeeded();
          await page.screenshot({path: path.join(output, `${width}-${lang}-text2x.jpg`), type: 'jpeg', quality: 80});
          await app.evaluate(() => document.documentElement.style.removeProperty('font-size'));
          await page.setViewportSize({width, height: 1000});
          row.text_enlargement = 'passed';
        }
        await select(app, 'duel_condition', tr('Com chuva registrada'));
        app = await ready(page, lang, {duelo_condicao: 'rain'});
        await compare(app, 'rain', 'win_rate', 5);
        const filters = app.getByRole('button', {name: tr('Filtros'), exact: false});
        await filters.click(); await select(app, 'pilot_metric', tr('Pódios'));
        app = await ready(page, lang, {metrica: 'podiums', duelo_condicao: 'rain'});
        await page.keyboard.press('Escape');
        await compare(app, 'rain', 'podiums', 5);
        app = await open({duelo_condicao: 'rain', minimo: '15'});
        await compare(app, 'rain', 'win_rate', 15);
        assert.equal(await app.locator('[data-testid=stMetricValue]').filter({hasText: '—'}).count(), 2);
        app = await open({anos: '2024', piloto: 'bortoleto'});
        await app.getByText(tr('Sem largadas em comum nesta condição. Experimente outro período ou condição.'), {exact: true}).waitFor();
        assert.equal(await app.locator('.fan-duel-difference').count(), 0, 'No shared starts must not create a comparison');
        app = await open();
        const other = lang === 'pt' ? 'en' : 'pt';
        await app.getByRole('button', {name: other === 'en' ? /🇬🇧/ : /🇧🇷/}).click();
        app = await ready(page, other, {visao: 'duelo', piloto: 'max_verstappen', rival: 'norris', anos: '2026', gp: '19'});
        await app.locator('.fan-duel-difference').filter({hasText: other === 'en' ? 'Difference in this selection' : 'Diferença no recorte'}).waitFor();
        await app.getByRole('button', {name: lang === 'en' ? /🇬🇧/ : /🇧🇷/}).click();
        app = await ready(page, lang);
        const motion = app.locator('[data-pw-motion]');
        await motion.click();
        await app.waitForFunction(() => document.documentElement.dataset.pwReducedMotion === 'true');
        assert.equal(await app.locator('.fan-duel-difference').evaluate(e => getComputedStyle(e).animationName), 'none');
        await page.emulateMedia({reducedMotion: 'reduce'});
        await app.waitForFunction(() => document.querySelector('[data-pw-motion]')?.disabled === true);
        assert.deepEqual(errors, []);
        row.status = 'passed';
      } catch (error) {
        row.status = 'failed'; row.error = error.stack;
        await page.screenshot({path: path.join(output, `${width}-${lang}-failure.jpg`), type: 'jpeg', quality: 75}).catch(() => {});
      } finally {
        report.cases.push(row); fs.writeFileSync(path.join(output, 'editorial.json'), JSON.stringify(report, null, 2));
        console.log(JSON.stringify({engine, width, lang, status: row.status, error: row.error})); await context.close();
      }
    }
  } finally { await browser.close(); }
  assert(report.cases.length === 4 && report.cases.every(row => row.status === 'passed'), 'Editorial acceptance failed');
})().catch(error => {console.error(error); process.exitCode = 1;});
