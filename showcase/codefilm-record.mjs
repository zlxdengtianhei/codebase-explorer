// Record the Flask code film on its deterministic virtual clock.
import puppeteer from 'puppeteer-core';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const arg = (key, fallback = null) => {
  const i = process.argv.indexOf('--' + key);
  return i < 0 ? fallback : process.argv[i + 1];
};
const out = arg('out'), fps = Number(arg('fps', 15));
const times = arg('times'), prefix = arg('prefix', 'codefilm');
const captionOut = arg('caption-out');
const chrome = arg('chrome', process.env.CHROME || '/usr/bin/google-chrome');
if (!out) { console.error('--out DIR is required'); process.exit(2); }
fs.mkdirSync(out, { recursive: true });
const types = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.woff2': 'font/woff2' };
const server = http.createServer((req, res) => {
  const relative = decodeURIComponent(req.url.split('?')[0]).replace(/^\/+/, '') || 'codefilm.html';
  const file = path.join(here, relative);
  if (!file.startsWith(here) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { 'content-type': types[path.extname(file)] || 'application/octet-stream' });
  fs.createReadStream(file).pipe(res);
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const browser = await puppeteer.launch({
  executablePath: chrome, headless: true,
  args: ['--no-sandbox', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=1', '--font-render-hinting=none', '--disable-lcd-text'],
});
const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 720, deviceScaleFactor: 1 });
page.on('console', message => { if (message.type() === 'error') console.error('page:', message.text()); });
page.on('pageerror', error => console.error('pageerror:', error.message));
await page.goto(`http://127.0.0.1:${server.address().port}/codefilm.html?record=1`);
await page.waitForFunction('window.__ready === true || window.__error', { timeout: 60000 });
const error = await page.evaluate('window.__error');
if (error) { console.error(error); process.exit(1); }
const shot = file => page.screenshot({ path: file, type: 'png', optimizeForSpeed: true, clip: { x: 0, y: 0, width: 1280, height: 720 } });
if (captionOut) {
  const segments = await page.evaluate('window.__captionSegments()');
  fs.writeFileSync(captionOut, segments.map(s =>
    `${s.id}.${s.segment} | ${s.t0.toFixed(6)}–${s.t1.toFixed(6)} | view ${s.view + 1} | ${s.lines} lines | ${s.text}`
  ).join('\n') + '\n');
  console.log(`${segments.length} caption segments in ${captionOut}`);
}
if (times) {
  for (const t of times.split(',').map(Number)) {
    await page.evaluate(t => window.__render(t), t);
    await shot(path.join(out, `${prefix}_${t.toFixed(2)}.png`));
    console.log(JSON.stringify(await page.evaluate(t => window.__state(t), t)));
  }
} else {
  const total = await page.evaluate('window.__total');
  const count = Math.ceil(total * fps);
  for (let k = 0; k < count; k++) {
    await page.evaluate(t => window.__render(t), k / fps);
    await shot(path.join(out, `frame_${String(k).padStart(5, '0')}.png`));
  }
  console.log(`${count} frames in ${out}`);
}
await browser.close(); server.close();
