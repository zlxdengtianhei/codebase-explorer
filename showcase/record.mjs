// Record the play-mode page frame by frame with headless Chrome.
//   node record.mjs --data cjson --out DIR [--fps 30] [--from 0 --to END]       numbered frames
//   node record.mjs --mode tour --data flask --out DIR --fps 15                  narrated-tour frames
//   node record.mjs --data flask --out DIR --times 3.8,10.8 --prefix flask     single named frames
//   node record.mjs --data cjson --out DIR --interactive hover.png             interactive-mode screenshot
import puppeteer from 'puppeteer-core';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i < 0 ? d : process.argv[i + 1]; };
const data = arg('data', 'cjson'), out = arg('out'), fps = +arg('fps', 30), from = +arg('from', 0), to = arg('to', null);
const times = arg('times', null), prefix = arg('prefix', 'shot'), inter = arg('interactive', null), lang = arg('lang', 'en');
const mode = arg('mode', 'play'), captionOut = arg('caption-out', null);
const chrome = arg('chrome', process.env.CHROME || ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'chrome']
  .flatMap(n => (process.env.PATH || '').split(path.delimiter).map(d => path.join(d, n))).find(p => fs.existsSync(p)));
if (!chrome) { console.error('no Chrome found; set CHROME=/path/to/chrome'); process.exit(2); }
if (!out) { console.error('--out DIR is required'); process.exit(2); }
fs.mkdirSync(out, { recursive: true });

const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.woff2': 'font/woff2' };
const server = http.createServer((req, res) => {
  const p = path.join(here, decodeURIComponent(req.url.split('?')[0]).replace(/^\/+/, '') || 'index.html');
  if (!p.startsWith(here) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { 'content-type': types[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(res);
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const base = `http://127.0.0.1:${server.address().port}/index.html`;

const browser = await puppeteer.launch({
  executablePath: chrome, headless: true,
  args: ['--no-sandbox', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=1', '--font-render-hinting=none', '--disable-lcd-text'],
});
const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 720, deviceScaleFactor: 1 });
page.on('console', m => { if (m.type() === 'error') console.error('page:', m.text()); });
page.on('pageerror', e => console.error('pageerror:', e.message));
const q = inter ? `?data=${data}&lang=${lang}` : `?mode=${mode}&record=1&data=${data}&lang=${lang}`;
await page.goto(base + q);
await page.waitForFunction('window.__ready === true || window.__error', { timeout: 60000 });
const err = await page.evaluate('window.__error'); if (err) { console.error(err); process.exit(1); }
if (captionOut) {
  const segments = await page.evaluate('window.__captionSegments()');
  for (let i = 0; i < segments.length; i++) {
    const s = segments[i], prev = segments[i - 1];
    if (s.lines > 2) throw new Error(`caption ${s.id}.${s.segment} has ${s.lines} lines`);
    if (prev && prev.id === s.id && Math.abs(prev.t1 - s.t0) > 1e-9) throw new Error(`caption gap at ${s.id}.${s.segment}`);
  }
  fs.writeFileSync(captionOut, segments.map(s =>
    `${s.id}.${s.segment} | ${s.t0.toFixed(6)}–${s.t1.toFixed(6)} | ${s.lines} lines | ${s.text}`
  ).join('\n') + '\n');
  console.log(`${segments.length} caption segments in ${captionOut}`);
}
const shot = f => page.screenshot({ path: f, type: 'png', optimizeForSpeed: true, clip: { x: 0, y: 0, width: 1280, height: 720 } });

if (inter) {
  const m = await page.evaluate('window.__model.focusUnit');
  await page.evaluate(`window.__render = null`);
  await new Promise(r => setTimeout(r, 300));
  const [x, y] = await page.evaluate(i => window.__unitScreen(i), m);
  const box = await (await page.$('#c')).boundingBox();
  await page.mouse.move(box.x + x * box.width / 1280, box.y + y * box.height / 720);
  await new Promise(r => setTimeout(r, 400));
  await shot(path.join(out, inter));
} else if (times) {
  for (const t of times.split(',').map(Number)) { await page.evaluate(t => window.__render(t), t); await shot(path.join(out, `${prefix}_${t.toFixed(2)}.png`)); }
} else {
  const end = to == null ? await page.evaluate('window.__total') : +to;
  const n = mode === 'tour' ? Math.ceil((end - from) * fps) : Math.round((end - from) * fps);
  for (let k = 0; k < n; k++) {
    await page.evaluate(t => window.__render(t), from + k / fps);
    await shot(path.join(out, `frame_${String(k).padStart(5, '0')}.png`));
  }
  console.log(`${n} frames in ${out}`);
}
await browser.close(); server.close();
