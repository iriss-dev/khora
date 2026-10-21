const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const root = path.resolve(__dirname, '..');
const server = http.createServer((req, res) => {
  let file = path.resolve(root, '.' + decodeURIComponent(new URL(req.url, 'http://localhost').pathname));
  if (!file.startsWith(root + path.sep) && file !== root) return res.writeHead(403).end();
  if (fs.existsSync(file) && fs.statSync(file).isDirectory()) file = path.join(file, 'index.html');
  const types = {'.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png'};
  fs.readFile(file, (error, data) => {
    if (error) return res.writeHead(404).end();
    res.setHeader('Content-Type', types[path.extname(file)] || 'application/octet-stream');
    res.end(data);
  });
});

(async () => {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  let browser;
  try {
    browser = await chromium.launch({channel: process.env.KHORA_BROWSER_CHANNEL || 'msedge', headless: true, args: ['--enable-unsafe-swiftshader']});
    const page = await browser.newPage({viewport: {width: 1536, height: 1000}});
    const errors = [], external = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
    await page.route('**/*', route => {
      const url = new URL(route.request().url());
      if (url.hostname !== '127.0.0.1' && !['data:', 'blob:'].includes(url.protocol)) {
        external.push(url.href);
        return route.abort();
      }
      return route.continue();
    });
    const base = `http://127.0.0.1:${server.address().port}`;
    await page.goto(base);
    await page.waitForFunction(() => document.getElementById('preview-pressure')?.textContent.includes('Pa'));
    assert.equal(await page.locator('html').getAttribute('lang'), 'es');
    await page.locator('#language').click();
    assert.match(await page.locator('h1').textContent(), /Beyond/);
    await page.reload();
    assert.equal(await page.locator('html').getAttribute('lang'), 'en');
    await page.locator('[data-rig="optics"]').click();
    assert.equal(await page.locator('[data-rig="optics"]').getAttribute('aria-pressed'), 'true');
    await page.locator('[data-rig="haptics"]').click();
    await page.locator('[data-rig="all"]').click();
    await page.locator('#rig-reset').click();
    const before = await page.locator('#preview-pressure').textContent();
    await page.locator('#preview-focus').fill('40');
    await page.waitForFunction(() => document.getElementById('preview-value').textContent === '40 mm');
    assert.notEqual(await page.locator('#preview-pressure').textContent(), before);
    await page.locator('#preview-open').click();
    await page.waitForFunction(() => document.getElementById('field-x-value')?.textContent === '40 mm');
    await page.goto(base + '/platform/');
    await page.waitForFunction(() => document.getElementById('preview-pressure').textContent.includes('Pa'));
    fs.mkdirSync(path.join(root, 'build'), {recursive: true});
    const layouts = [];
    for (const width of [1536, 768, 390, 360]) {
      await page.setViewportSize({width, height: width > 768 ? 1000 : 844});
      const measured = await page.evaluate(() => ({width: innerWidth, content: document.documentElement.scrollWidth}));
      assert.ok(measured.content <= measured.width, JSON.stringify(measured));
      layouts.push(measured);
      await page.screenshot({path: path.join(root, `build/landing-${width}.png`), fullPage: true});
    }
    const localLinks = await page.locator('a[href]').evaluateAll(elements => [...new Set(elements.map(a => a.href).filter(href => href.startsWith(location.origin)))]);
    for (const href of localLinks) assert.ok((await page.request.get(href)).ok(), href);
    const fallback = await browser.newPage();
    await fallback.addInitScript(() => {
      const getContext = HTMLCanvasElement.prototype.getContext;
      HTMLCanvasElement.prototype.getContext = function (kind, ...args) {
        return kind.includes('webgl') ? null : getContext.call(this, kind, ...args);
      };
    });
    await fallback.goto(base + '/platform/');
    assert.equal(await fallback.locator('#rig-fallback').isVisible(), true);
    assert.equal(await fallback.locator('#preview-error').isVisible(), true);
    assert.match(await fallback.locator('#preview-pressure').textContent(), /Pa/);
    assert.equal(await fallback.locator('#rig-fallback img').evaluate(img => img.complete && img.naturalWidth > 0), true);
    assert.deepEqual(errors, []);
    assert.deepEqual(external, []);
    console.log(JSON.stringify({result: 'passed', layouts, checkedLinks: localLinks.length, browserErrors: errors.length, externalRequests: external.length, webglFallback: true}, null, 2));
  } finally {
    await browser?.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
