/* Served profile photos: identity, original bytes and DPR2 delivery capacity.
 * Focus, expression and head framing still require the separate visual review.
 */
const fs = require('node:fs'), path = require('node:path'), assert = require('node:assert/strict');
const crypto = require('node:crypto');
const pw = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const {surface} = require('./app_surface.cjs');
const {verifyImage} = require('./verificar_publicacao.cjs');
const [base, output] = process.argv.slice(2);
assert(base && output, 'Usage: aceite_fotos_perfil.cjs URL OUTPUT');
const engine = process.env.PLAYWRIGHT_BROWSER || 'chromium';
const root = path.resolve(process.env.PITWALL_SOURCE_ROOT || path.join(__dirname, '../..'));
const report = {schema:'pitwall-profile-photo-acceptance-v1', engine, base, status:'failed',
  started_utc:new Date().toISOString(), dpr:2, cases:[], errors:[],
  manual_review:'Focus, facial detail, expression and head/cap framing are not assessed by these assertions.'};
fs.mkdirSync(output, {recursive:true});
function save() {
  const file = path.join(output, 'profile-photos.json');
  fs.writeFileSync(file + '.tmp', JSON.stringify(report, null, 2));
  fs.renameSync(file + '.tmp', file);
}
const digest = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const normalise = value => value.replace(/\s+/g, ' ').trim();
const locationOnly = value => {try {const u = new URL(value);return u.origin + u.pathname;} catch {return value;}};

async function ready(app, driver, photo, lang, version) {
  await app.getByText('v' + version, {exact:true}).first().waitFor({timeout:90000});
  await app.waitForFunction(({driver,lang}) => {
    const q = new URL(location.href).searchParams;
    return document.documentElement.lang === lang && q.get('tela') === 'Pilotos' &&
      q.get('visao') === 'perfil' && q.get('piloto') === driver &&
      document.querySelector('.stApp')?.dataset.testScriptState === 'notRunning' &&
      document.querySelectorAll('.fan-hero-profile-editorial').length === 1 &&
      document.querySelector('.fan-hero-profile-editorial')?.dataset.driverId === driver &&
      document.querySelectorAll('.st-key-pw-sidebar-menu button').length === 15;
  }, {driver,lang}, {timeout:90000});
  const hero = app.locator('.fan-hero-profile-editorial[data-driver-id="' + driver + '"]');
  assert.equal(normalise(await hero.locator('h1').innerText()), photo.name, 'Profile heading has another identity');
  const favourite = app.frameLocator('iframe[src*="pitwall_favorite"]');
  await favourite.locator('option[value="max_verstappen"]').waitFor({state:'attached',timeout:30000});
  await favourite.getByText(lang === 'pt' ? 'Seu piloto favorito · salvo neste navegador' :
    'Your favourite driver · saved in this browser', {exact:true}).waitFor({timeout:30000});
  await app.evaluate(() => {window.pwProfilePhotoIdle = 0;});
  await app.waitForFunction(() => {
    if (document.querySelector('.stApp')?.dataset.testScriptState !== 'notRunning') {
      window.pwProfilePhotoIdle = 0;return false;
    }
    window.pwProfilePhotoIdle ||= performance.now();
    return performance.now() - window.pwProfilePhotoIdle >= 1200;
  }, null, {timeout:30000});
  await app.evaluate(async () => {
    await document.fonts.ready;
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  });
  await hero.locator('.fan-hero-candid').evaluate(img => img.decode());
  assert.equal(await app.locator('[data-testid=stException]').count(), 0, 'Streamlit exception');
  assert.equal(await app.locator('[data-testid=stAlertContentError]:visible').count(), 0, 'Visible widget error');
  return hero;
}

async function inspect(hero) {
  return hero.evaluate(hero => {
    const rect = element => {const r = element.getBoundingClientRect();return {x:r.x,y:r.y,right:r.right,
      bottom:r.bottom,width:r.width,height:r.height};};
    const img = hero.querySelector('.fan-hero-candid'), imageRect = img.getBoundingClientRect(), style = getComputedStyle(img);
    const crop = img.closest('.pw-profile-image-window--crop'), visible = crop || img;
    const r = visible.getBoundingClientRect();
    const clips = [];
    for (let node = visible.parentElement; node; node = node.parentElement) {
      const css = getComputedStyle(node);
      if (['hidden','clip','auto','scroll'].includes(css.overflowX)) {
        const b = node.getBoundingClientRect(), left = b.left + node.clientLeft;
        clips.push({element:node.dataset.testid || node.tagName, overflow:css.overflowX,
          left, right:left + node.clientWidth, clipped:r.left < left - 1 || r.right > left + node.clientWidth + 1});
      }
    }
    const sourceView = crop ? {
      left:100 * (r.left-imageRect.left) / imageRect.width,
      top:100 * (r.top-imageRect.top) / imageRect.height,
      right:100 * (imageRect.right-r.right) / imageRect.width,
      bottom:100 * (imageRect.bottom-r.bottom) / imageRect.height,
      width:img.naturalWidth * r.width / imageRect.width,
      height:img.naturalHeight * r.height / imageRect.height,
    } : null;
    return {natural:[img.naturalWidth,img.naturalHeight], display:rect(visible), rendered_image:rect(img),
      crop_window:crop && rect(crop), source_view:sourceView, transform:style.transform, hero:rect(hero),
      figure:rect(img.closest('figure')), dpr:devicePixelRatio, fit:style.objectFit,
      mask:style.maskImage || style.webkitMaskImage || 'none', clip:style.clipPath,
      capacity:Math.min(img.naturalWidth / imageRect.width, img.naturalHeight / imageRect.height),
      overflow:document.documentElement.scrollWidth > innerWidth + 1,
      viewport:innerWidth, clipping_ancestors:clips, source_path:new URL(img.currentSrc).pathname,
      alt:img.alt};
  });
}

async function run() {
  let browser;
  try {
    const url = new URL(base);
    assert(url.protocol === 'https:' || ['127.0.0.1','localhost'].includes(url.hostname), 'Use HTTPS or loopback');
    assert(['chromium','webkit','firefox'].includes(engine), 'Unsupported browser engine');
    const version = fs.readFileSync(path.join(root, 'VERSION'), 'utf8').trim();
    assert(/^\d+\.\d+\.\d+$/.test(version), 'Invalid expected version');
    const raw = fs.readFileSync(path.join(root, 'frontend_assets/profile_photos.json'));
    const catalogue = JSON.parse(raw);
    assert.equal(catalogue.schema, 1, 'Unexpected profile photo catalogue schema');
    const allPhotos = Object.entries(catalogue.photos);
    report.deferred_driver_ids = Object.keys(catalogue.deferred_profiles || {});
    assert(allPhotos.length && allPhotos.some(([id]) => id === 'antonelli') &&
      allPhotos.some(([id]) => id === 'max_verstappen'), 'Approved profile identities are missing');
    const selected = process.env.PITWALL_PROFILE_IDS?.split(',');
    const photos = selected ? selected.map(id => {
      const photo = allPhotos.find(([driver]) => driver === id);
      assert(photo, 'Requested review identity is missing: ' + id);return photo;
    }) : allPhotos;
    if (selected) assert.equal(new Set(selected).size, selected.length, 'Duplicate review identity');
    report.selected_driver_ids = selected || null;
    report.version = version;report.catalogue_sha256 = digest(raw);
    report.verifier_sha256 = digest(fs.readFileSync(__filename));
    report.expected_cases = photos.length * 4;
    for (const [driver, photo] of allPhotos) {
      assert(/^[a-z0-9_]+$/.test(driver) && photo.driver_id === driver, 'Invalid photo identity');
      assert(/^[a-f0-9]{64}$/.test(photo.sha256), 'Invalid photo digest');
      assert.equal(photo.path, `static/pitwall-profiles/${driver}-${photo.sha256.slice(0,12)}.jpg`, 'Unexpected immutable photo path');
      assert(Number.isInteger(photo.width) && Number.isInteger(photo.height) && photo.width > 0 && photo.height > 0, 'Invalid dimensions');
      assert(Array.isArray(photo.caption) && photo.caption.length === 2 && photo.caption.every(v => typeof v === 'string' && v), 'Missing bilingual caption');
      assert.equal(digest(fs.readFileSync(path.join(root, photo.path))), photo.sha256, 'Expected local photo differs from catalogue');
    }
    save();
    const launch = {headless:true};
    if (engine === 'chromium' && process.env.PLAYWRIGHT_CHANNEL) launch.channel = process.env.PLAYWRIGHT_CHANNEL;
    browser = await pw[engine].launch(launch);
    for (const [driver, photo] of photos) for (const width of [1440,390]) for (const lang of ['pt','en']) {
      const row = {driver,width,lang,dpr:2,status:'running',pageerrors:[]};report.cases.push(row);save();
      const context = await browser.newContext({viewport:{width,height:1000},deviceScaleFactor:2,
        isMobile:width === 390,hasTouch:width === 390});
      const tracked = new WeakSet();
      function track(page) {
        if (tracked.has(page)) return;tracked.add(page);
        page.on('pageerror', error => {
          const item = {driver,width,lang,message:error.message,stack:error.stack,url:locationOnly(page.url()),utc:new Date().toISOString()};
          row.pageerrors.push(item);report.errors.push(item);row.status='failed';save();
        });
      }
      context.on('page', track);
      const page = await context.newPage();track(page);
      const stem = `${engine}-${driver}-${lang}-${width}-2x`;
      try {
        await page.goto(base.replace(/\/$/, '') + '/?' + new URLSearchParams({tela:'Pilotos',visao:'perfil',
          piloto:driver,anos:'2024,2025,2026',temporada:'2026',gp:'18',lang}), {waitUntil:'domcontentloaded',timeout:90000});
        const app = await surface(page,base), hero = await ready(app,driver,photo,lang,version);
        const selector = `.fan-hero-profile-editorial[data-driver-id="${driver}"] .fan-hero-candid`;
        row.served_image = await verifyImage(page,app,{selector,static_path:photo.path,sha256:photo.sha256});
        assert.equal(row.served_image.delivery, 'static_original', 'Editorial photo must use its immutable original');
        assert.equal(row.served_image.width, photo.width, 'Served natural width differs');
        assert.equal(row.served_image.height, photo.height, 'Served natural height differs');
        const m = await inspect(hero);row.geometry=m;
        assert.equal(m.dpr, 2, 'Capture is not DPR2');
        assert(m.display.width > 0 && m.display.height > 0 && m.capacity >= 2, 'Source cannot support displayed photo at DPR2');
        assert(!m.overflow, 'Horizontal page overflow');
        for (const box of [m.hero,m.figure,{x:0,right:m.viewport}]) {
          assert(m.display.x >= box.x - 1 && m.display.right <= box.right + 1, 'Photo escapes its horizontal frame');
        }
        assert(!m.clipping_ancestors.some(c => c.clipped), 'An ancestor clips the photo horizontally');
        assert.equal(m.clip, 'none', 'Unexpected photo clip path');
        assert.equal(m.mask, 'none', 'Unexpected photo mask');
        assert.equal(Boolean(m.crop_window), Boolean(photo.focal_crop), 'Unexpected focal crop window');
        if (photo.focal_crop) {
          assert.equal(m.transform, 'none', 'Focal framing must retain the source pixel mapping');
          assert(Math.abs(m.rendered_image.width / m.rendered_image.height - photo.width / photo.height) < .001,
            'Focal photograph is stretched');
          for (const side of ['top','right','bottom','left']) {
            assert(Math.abs(m.source_view[side] - photo.focal_crop[side]) < .01, 'Focal source edge differs: ' + side);
          }
          assert(m.source_view.width >= 1600 && m.source_view.height >= 1600, 'Focal window discards too many native pixels');
          assert(Math.min(m.source_view.width / m.display.width, m.source_view.height / m.display.height) >= 2,
            'Visible source pixels cannot support DPR2');
        }
        assert.equal(m.alt, photo.caption[lang === 'en' ? 1 : 0], 'Photo alt text differs from expected identity/context');
        const caption = hero.locator('figcaption');
        row.caption = normalise(await caption.innerText());
        assert.equal(row.caption, normalise(`${photo.caption[lang === 'en' ? 1 : 0]} ${photo.author} · ${photo.license}`), 'Bilingual photo credit differs');
        assert.equal(await caption.getByRole('link',{name:photo.author,exact:true}).getAttribute('href'), photo.source, 'Author/source link differs');
        assert.equal(await caption.getByRole('link',{name:photo.license,exact:true}).getAttribute('href'), photo.license_url, 'License link differs');
        row.screenshots={page:stem + '-page.png',photo:stem + '-photo.png'};
        await page.screenshot({path:path.join(output,row.screenshots.page)});
        await hero.locator(photo.focal_crop ? '.pw-profile-image-window--crop' : '.fan-hero-candid')
          .screenshot({path:path.join(output,row.screenshots.photo)});
        assert.equal(row.pageerrors.length, 0, 'Unfiltered browser pageerror');
        row.status='passed';save();
        console.log(JSON.stringify({engine,driver,width,lang,status:row.status}));
      } catch (error) {
        row.status='failed';row.error=error.stack || error.message;save();
        await page.screenshot({path:path.join(output,stem + '-failed.png'),timeout:5000}).catch(() => {});
        throw error;
      } finally {await context.close();save();}
    }
    assert.equal(report.errors.length, 0, 'Unfiltered browser errors were retained in profile-photos.json');
    assert.equal(report.cases.length, report.expected_cases, 'Incomplete photo matrix');
    assert(report.cases.every(row => row.status === 'passed'), 'Some photo cases failed');
    report.status='passed';
  } catch (error) {
    report.status='failed';report.error=error.stack || error.message;throw error;
  } finally {
    if (browser) await browser.close();
    if (report.errors.length) report.status='failed';
    report.finished_utc=new Date().toISOString();save();
  }
  assert.equal(report.status, 'passed', 'Photo acceptance failed; retained profile-photos.json has details');
}
run().catch(error => {console.error(error.stack || error.message);process.exitCode=1;});
