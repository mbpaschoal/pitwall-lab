/* Real Streamlit geometry: cover, podium and the separate driver profile. */
const fs = require('node:fs'), path = require('node:path'), assert = require('node:assert/strict');
const pw = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const {surface} = require('./app_surface.cjs');
const [base, output] = process.argv.slice(2);
assert(base && output, 'Usage: aceite_diagramacao.cjs URL OUTPUT');
const engine = process.env.PLAYWRIGHT_BROWSER || 'chromium';
const root = path.resolve(process.env.PITWALL_SOURCE_ROOT || path.join(__dirname, '../..'));
const version = fs.readFileSync(path.join(root, 'VERSION'), 'utf8').trim();
const report = {engine, base, version, status:'failed', cases: [], errors: []};
fs.mkdirSync(output, {recursive: true});
const close = (a, b, label) => assert(Math.abs(a - b) <= 1, `${label}: ${a} / ${b}`);
async function ready(app, selector, lang) {
  await app.waitForFunction(({selector,lang,version}) => document.querySelector('.stApp')?.dataset.testScriptState === 'notRunning' &&
    document.documentElement.lang === lang && document.querySelector('.st-key-journey-header')?.innerText.includes('v' + version) &&
    !!document.querySelector(selector) && document.querySelectorAll('.st-key-pw-sidebar-menu button').length === 15,
  {selector,lang,version}, {timeout: 90000});
  if (selector === '.fan-hero-profile-editorial') {
    const driver = app.locator('.st-key-pilot-profile-selector').getByRole('combobox');
    await driver.waitFor();
    assert.equal(await app.locator('iframe[src*="pitwall_favorite"]').count(), 0);
    assert(await driver.evaluate(control => control.getBoundingClientRect().bottom <=
      document.querySelector('.fan-hero-profile-editorial').getBoundingClientRect().top), 'Driver selector must precede the profile cover');
  }
  await app.evaluate(() => document.fonts.ready);
  await app.locator(selector + ' img').evaluateAll(imgs => Promise.all(imgs.map(img => img.decode())));
  assert.equal(await app.locator('[data-testid=stException]').count(), 0);
}
async function geometry(app, kind) {
  return app.evaluate(kind => {
    const rect = e => { const r = e.getBoundingClientRect(); return {x:r.x, y:r.y, right:r.right, bottom:r.bottom, width:r.width, height:r.height}; };
    const hero = document.querySelector(kind === 'result' ? '.pw-postcard' : '.fan-hero-profile-editorial');
    const img = hero.querySelector('img'), h1 = hero.querySelector('h1');
    const control = document.querySelector('.st-key-pilot-view-navigation button');
    const caption = document.querySelector('.st-key-pilot-heading-toolbar [data-testid=stCaptionContainer]');
    // Streamlit mounts both responsive popover triggers; measure the visible one.
    const search = [...document.querySelectorAll('.st-key-topbar [data-testid=stPopoverButton]')].find(e => e.getBoundingClientRect().width > 0);
    const filter = [...document.querySelectorAll('.st-key-pilot-comparison-toolbar button')].find(e => e.getBoundingClientRect().width > 0);
    const scope = document.querySelector('.fan-pilot-toolbar');
    const podium = document.querySelector('.fan-podium-panel'), circuit = document.querySelector('.fan-circuit-details');
    return {hero:rect(hero), img:rect(img), h1:rect(h1), fit:getComputedStyle(img).objectFit,
      natural:[img.naturalWidth,img.naturalHeight], control:control && rect(control), label:control && rect(control.querySelector('p')),
      caption:caption && rect(caption), search:search && rect(search), podium:podium && rect(podium), circuit:circuit && rect(circuit),
      filter:filter && rect(filter), scope:scope && rect(scope),
      overflow:document.documentElement.scrollWidth > innerWidth + 1,
      radius:getComputedStyle(img).borderRadius, shadow:getComputedStyle(img).boxShadow,
      profiles:document.querySelectorAll('.fan-hero-profile-editorial,[data-hero-kind=profile]').length};
  }, kind);
}
function check(m, kind, width) {
  assert(!m.overflow, 'Page overflows horizontally');
  assert(m.img.x >= m.hero.x - 1 && m.img.right <= m.hero.right + 1, 'Image escaped its own column');
  assert(m.img.x >= 0 && m.img.right <= width + 1, 'Image escaped viewport');
  assert(m.natural.every(n => n > 0), 'Image did not load');
  assert(m.h1.x >= m.hero.x - 1 && m.h1.right <= m.hero.right + 1, 'Heading escaped cover');
  if (kind === 'result') {
    close(m.img.x, m.hero.x, 'Cover left edge'); close(m.img.right, m.hero.right, 'Cover right edge');
    close(m.img.height, m.img.width * m.natural[1] / m.natural[0], 'Original painting aspect ratio');
    assert.equal(m.fit, 'contain', 'Painting must retain the complete car and scene');
    assert(m.h1.y >= m.img.y && m.h1.bottom <= m.img.bottom, 'Title is not over the painting');
    assert(parseFloat(m.radius) > 0 && m.shadow !== 'none', 'Rounded cover / discreet shadow missing');
    assert.equal(m.profiles, 0, 'A driver profile was inserted on the race result');
    if (Math.abs(m.podium.y - m.circuit.y) <= 1) close(m.podium.bottom, m.circuit.bottom, 'Panel bottom alignment');
    else assert(m.circuit.y >= m.podium.bottom + 7, 'Stacked result panels overlap');
  } else {
    close(m.control.right, m.hero.right, 'Explore drivers right edge');
    close(m.control.y + m.control.height / 2, m.label.y + m.label.height / 2, 'Explore label vertical center');
    close(m.search.y, m.control.y, 'Search and explore controls share a row');
    close(m.search.bottom, m.control.bottom, 'Search and explore target heights');
    assert(m.search.right <= m.control.x - 7, 'Search and explore overlap');
    assert(m.control.height >= 44, 'Explore target is too short');
    close(m.filter.right, m.hero.right, 'Filters right edge');
    assert(m.filter.height >= 44, 'Filters target is too short');
    if (width > 600) close(m.caption.y + m.caption.height / 2, m.control.y + m.control.height / 2, 'Coverage/control vertical center');
    else assert(m.control.y >= m.caption.bottom + 7, 'Mobile control overlaps coverage');
    if (width > 600) close(m.scope.y + m.scope.height / 2, m.filter.y + m.filter.height / 2, 'Scope/filter vertical center');
    else assert(m.filter.y >= m.scope.bottom + 7, 'Mobile filters overlap comparison scope');
  }
}
(async () => {
  const options = {headless: true};
  if (engine === 'chromium' && process.env.PLAYWRIGHT_CHANNEL) options.channel = process.env.PLAYWRIGHT_CHANNEL;
  const browser = await pw[engine].launch(options);
  try {
    for (const width of [320,390,768,1024,1440]) for (const lang of ['pt','en']) for (const kind of ['result','profile']) {
      const context = await browser.newContext({viewport:{width,height:1000},isMobile:width < 601,hasTouch:width < 601});
      const page = await context.newPage();
      page.on('pageerror', e => report.errors.push({width,lang,kind,message:e.message}));
      try {
        const query = kind === 'result' ? {tela:'Corridas',temporada:2026,gp:18,lang} : {tela:'Pilotos',visao:'perfil',piloto:'antonelli',anos:2026,lang};
        await page.goto(base + '/?' + new URLSearchParams(query));
        const app = await surface(page,base);
        await ready(app, kind === 'result' ? '.pw-postcard' : '.fan-hero-profile-editorial',lang);
        const m = await geometry(app,kind); check(m,kind,width);
        await page.screenshot({path:path.join(output,`${kind}-${lang}-${width}.png`)});
        if (kind === 'result') {
          await app.locator('.st-key-race-summary').scrollIntoViewIfNeeded();
          await page.screenshot({path:path.join(output,`podium-${lang}-${width}.png`)});
        } else {
          await app.locator('.st-key-pilot-view-navigation button').click();
          await app.locator('[data-testid=stPopoverBody]:visible').getByText(lang === 'pt' ? 'Duelo' : 'Head to head', {exact:true}).click({timeout:5000});
          await app.locator('.st-key-duel-stage').waitFor();
          assert.equal(await app.locator('[data-testid=stException]').count(),0);
        }
        report.cases.push({width,lang,kind,geometry:m,status:'passed'});
        console.log(`${engine} ${kind} ${lang} ${width} passed`);
      } catch(error) {
        report.cases.push({width,lang,kind,status:'failed',error:error.stack});
        await page.screenshot({path:path.join(output,`${kind}-${lang}-${width}-failed.png`)}).catch(()=>{});
        throw error;
      } finally {await context.close();}
    }
    assert.equal(report.errors.length,0,JSON.stringify(report.errors));
    report.status = 'passed';
  } finally {
    await browser.close();
    fs.writeFileSync(path.join(output,'layout-report.json'),JSON.stringify(report,null,2));
  }
})().catch(e => {console.error(e);process.exit(1);});
