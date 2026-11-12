/* Flask source film: exact excerpts, catalog location, and deterministic captions. */
(() => {
'use strict';
const W = 1280, H = 720;
const SANS = '"IBM Plex Sans", system-ui, sans-serif';
const MONO = '"IBM Plex Mono", ui-monospace, monospace';
const C = { bg: '#06101b', panel: '#091724', ink: '#e8f1ff', muted: '#9fb6cc', dim: '#668198', teal: '#6ee7d0', gold: '#f6c76c' };
const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
let data, timing;

const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
function text(s, x, y, font, color = C.ink, align = 'left', alpha = 1) {
  ctx.globalAlpha = alpha; ctx.font = font; ctx.fillStyle = color; ctx.textAlign = align; ctx.textBaseline = 'alphabetic';
  ctx.fillText(s, x, y); ctx.globalAlpha = 1;
}
function width(s, font) { ctx.font = font; return ctx.measureText(s).width; }
function fit(s, font, max) {
  if (width(s, font) <= max) return s;
  while (s.length > 1 && width(s + '…', font) > max) s = s.slice(0, -1);
  return s.trimEnd() + '…';
}
function wrap(s, font, max) {
  const words = s.split(/\s+/).filter(Boolean), lines = [];
  let line = '';
  for (const word of words) {
    const candidate = line ? line + ' ' + word : word;
    if (!line || width(candidate, font) <= max) line = candidate;
    else { lines.push(line); line = word; }
  }
  if (line) lines.push(line);
  return lines;
}
function rrect(x, y, w, h, r) { ctx.beginPath(); ctx.roundRect(x, y, w, h, r); }
function background() {
  const gradient = ctx.createLinearGradient(0, H, W, 0);
  gradient.addColorStop(0, '#040b13'); gradient.addColorStop(0.58, '#091827'); gradient.addColorStop(1, '#123146');
  ctx.fillStyle = gradient; ctx.fillRect(0, 0, W, H);
  const glow = ctx.createRadialGradient(1170, 20, 0, 1170, 20, 550);
  glow.addColorStop(0, 'rgba(59,160,170,.14)'); glow.addColorStop(1, 'rgba(59,160,170,0)');
  ctx.fillStyle = glow; ctx.fillRect(0, 0, W, H);
}
function sentences(caption) { return caption.split(/(?<=[.!?])\s+/).filter(Boolean); }
function captionSegments(cue, item) {
  const parts = sentences(item.caption || item.say);
  const total = parts.reduce((n, s) => n + s.length, 0);
  let start = cue.t0;
  return parts.map((part, index) => {
    const end = index === parts.length - 1 ? cue.t1 : start + (cue.t1 - cue.t0) * part.length / total;
    const segment = { id: cue.id, segment: index + 1, view: index, t0: start, t1: end, text: part, lines: wrap(part, `400 28px ${SANS}`, 1160) };
    start = end;
    return segment;
  });
}
function allSegments() {
  return timing.items.flatMap((cue, i) => captionSegments(cue, data.items[i]));
}
function stateAt(t) {
  let index = 0;
  for (let i = 0; i < timing.items.length; i++) if (t >= timing.items[i].t0) index = i;
  const cue = timing.items[index], item = data.items[index];
  const segment = captionSegments(cue, item).find(s => t >= s.t0 && t < s.t1);
  const viewIndex = segment ? segment.view : item.views.length - 1;
  return { index, cue, item, segment, view: item.views[viewIndex], viewIndex, t };
}
function ancestorChain(id) {
  const chain = [];
  for (let node = data.nodes[id]; node; node = data.nodes[node.parent]) { chain.unshift(id); id = node.parent; }
  return chain.filter(Boolean);
}
function drawHeader(S) {
  text('FLASK', 36, 45, `600 29px ${SANS}`, C.ink);
  text('ONE REQUEST THROUGH THE CODE', 137, 44, `500 16px ${MONO}`, C.teal);
  text(`${String(S.index + 1).padStart(2, '0')}  /  ${data.items.length}`, 1244, 43, `500 17px ${MONO}`, C.muted, 'right');
  text(S.item.title, 36, 82, `600 26px ${SANS}`, C.ink);
  const dotW = 17, gap = 8, total = data.items.length * dotW + (data.items.length - 1) * gap;
  data.items.forEach((item, i) => {
    const x = W - 36 - total + i * (dotW + gap);
    ctx.fillStyle = i === S.index ? C.teal : i < S.index ? '#365d68' : '#24384a';
    rrect(x, 72, dotW, 4, 2); ctx.fill();
  });
}
function unitLabel(signature) {
  const lines = signature.split('\n');
  const start = lines.findIndex(l => /^\s*(def|class)\s/.test(l));
  return (start >= 0 ? lines.slice(start) : lines).join(' ').replace(/\s+/g, ' ').trim();
}
function drawCode(S) {
  const x = 36, y = 110, w = 870, h = 480, view = S.view;
  ctx.fillStyle = 'rgba(5,15,26,.94)'; rrect(x, y, w, h, 13); ctx.fill();
  ctx.strokeStyle = 'rgba(118,166,194,.24)'; ctx.lineWidth = 1; ctx.stroke();
  const paths = [...new Set(view.blocks.map(b => b.path))];
  text(fit(paths.join('  +  '), `500 15px ${MONO}`, w - 40), x + 20, y + 30, `500 15px ${MONO}`, C.teal);
  text(fit(unitLabel(view.unit), `500 16px ${MONO}`, w - 40), x + 20, y + 57, `500 16px ${MONO}`, C.muted);
  ctx.fillStyle = '#1b3245'; ctx.fillRect(x + 20, y + 72, w - 40, 1);

  const rows = [];
  view.blocks.forEach((block, bi) => {
    if (bi) rows.push({ gap: true });
    block.lines.forEach((line, i) => rows.push({ line, number: block.first + i, hot: block.highlights.includes(block.first + i) }));
  });
  const maxChars = Math.max(...rows.map(r => r.line ? r.line.length : 0));
  const lineH = Math.min(17.2, 365 / rows.length);
  const fontSize = Math.min(15, lineH - 0.7, 735 / Math.max(1, maxChars * 0.601));
  const font = `400 ${fontSize}px ${MONO}`;
  let ty = y + 96;
  ctx.save(); ctx.beginPath(); ctx.rect(x + 12, ty - lineH, w - 24, 374); ctx.clip();
  for (const row of rows) {
    if (row.gap) {
      text('⋮', x + 48, ty, `400 ${Math.max(11, fontSize)}px ${MONO}`, C.dim, 'center');
      ty += lineH * 0.72;
      continue;
    }
    if (row.hot) {
      const pulse = 0.13 + 0.025 * Math.sin(S.t * 3.2);
      ctx.fillStyle = `rgba(57,210,184,${pulse})`; ctx.fillRect(x + 13, ty - lineH + 2, w - 26, lineH);
      ctx.fillStyle = C.teal; ctx.fillRect(x + 13, ty - lineH + 2, 3, lineH);
    }
    text(String(row.number), x + 53, ty, font, row.hot ? C.teal : C.dim, 'right');
    const trimmed = row.line.trimStart();
    const color = !trimmed ? C.ink : trimmed.startsWith('#') || trimmed.startsWith('"""') ? '#7892a8' : row.hot ? '#ecfdf8' : '#cfdeed';
    text(row.line, x + 72, ty, font, color);
    ty += lineH;
  }
  ctx.restore();
  const ranges = view.blocks.map(b => `${b.first}–${b.last}`).join(' · ');
  text(`EXACT SOURCE  ·  LINES ${ranges}`, x + 20, y + h - 16, `500 12px ${MONO}`, C.dim);
}
function drawMap(S) {
  const x = 926, y = 110, w = 318, h = 480;
  ctx.fillStyle = 'rgba(5,15,26,.90)'; rrect(x, y, w, h, 13); ctx.fill();
  ctx.strokeStyle = 'rgba(118,166,194,.24)'; ctx.lineWidth = 1; ctx.stroke();
  text('MODULE MAP', x + 18, y + 30, `600 14px ${MONO}`, C.muted);
  const chain = ancestorChain(S.view.node);
  const top = chain.find(id => data.tops.includes(id));
  let ty = y + 59;
  data.tops.forEach(id => {
    const active = id === top, node = data.nodes[id];
    ctx.fillStyle = active ? 'rgba(110,231,208,.15)' : 'rgba(93,128,153,.055)';
    rrect(x + 14, ty - 18, w - 28, 28, 6); ctx.fill();
    if (active) { ctx.fillStyle = C.teal; ctx.fillRect(x + 14, ty - 18, 3, 28); }
    text(fit(node.title, `${active ? 600 : 400} 13px ${SANS}`, w - 48), x + 26, ty, `${active ? 600 : 400} 13px ${SANS}`, active ? C.teal : C.dim);
    ty += 32;
  });
  const cardY = y + 333;
  ctx.fillStyle = '#173447'; ctx.fillRect(x + 18, cardY - 19, w - 36, 1);
  text('YOU ARE HERE', x + 18, cardY, `500 11px ${MONO}`, C.dim);
  const titles = wrap(data.nodes[S.view.node].title, `600 17px ${SANS}`, w - 36);
  titles.slice(0, 2).forEach((line, i) => text(line, x + 18, cardY + 29 + i * 21, `600 17px ${SANS}`, C.ink));
  const parents = chain.filter(id => id !== S.view.node && id !== 'flask-web-framework');
  const path = parents.map(id => data.nodes[id].title).join('  ›  ') || 'Flask Web Framework';
  const parentLines = wrap(path, `400 12px ${SANS}`, w - 36);
  parentLines.slice(0, 3).forEach((line, i) => text(line, x + 18, cardY + 81 + i * 16, `400 12px ${SANS}`, C.muted));
}
function drawSubtitle(S) {
  if (!S.segment) return;
  const lines = S.segment.lines;
  const font = `400 28px ${SANS}`, lineH = 35;
  const widest = Math.max(...lines.map(l => width(l, font)));
  const boxH = lines.length * lineH + 20, bottom = 704;
  ctx.fillStyle = 'rgba(2,8,14,.93)'; rrect(W / 2 - widest / 2 - 24, bottom - boxH, widest + 48, boxH, 12); ctx.fill();
  lines.forEach((line, i) => text(line, W / 2, bottom - 14 - (lines.length - 1 - i) * lineH, font, '#f2f7ff', 'center'));
}
function render(t) {
  const S = stateAt(t);
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.clearRect(0, 0, W, H);
  background(); drawHeader(S); drawCode(S); drawMap(S);
  text('explanations generated by Codebase Explorer', 1244, 604, `400 11px ${SANS}`, C.dim, 'right');
  drawSubtitle(S);
}
async function boot() {
  const fonts = [
    ['IBM Plex Sans', 'IBMPlexSans-Regular.woff2', '400'], ['IBM Plex Sans', 'IBMPlexSans-SemiBold.woff2', '600'],
    ['IBM Plex Mono', 'IBMPlexMono-Regular.woff2', '400'], ['IBM Plex Mono', 'IBMPlexMono-Medium.woff2', '500'],
  ];
  await Promise.all(fonts.map(async ([family, file, weight]) => {
    const font = new FontFace(family, `url(fonts/${file})`, { weight }); await font.load(); document.fonts.add(font);
  }));
  [data, timing] = await Promise.all([
    fetch('data/codefilm.json').then(r => r.json()),
    fetch('tour/codefilm.en.timing.json').then(r => r.json()),
  ]);
  const segments = allSegments();
  const bad = segments.find(s => s.lines.length > 2);
  if (bad) throw new Error(`caption ${bad.id}.${bad.segment} has ${bad.lines.length} lines`);
  window.__total = timing.duration;
  window.__render = render;
  window.__captionSegments = () => allSegments().map(s => ({ ...s, lines: s.lines.length }));
  window.__state = t => {
    const S = stateAt(t);
    return { id: S.item.id, view: S.viewIndex, node: S.view.node, caption: S.segment && S.segment.text,
      source: S.view.blocks.map(b => ({ path: b.path, first: b.first, last: b.last, highlights: b.highlights })) };
  };
  window.__ready = true;
  if (new URLSearchParams(location.search).has('record')) render(0);
  else { const start = performance.now(); const loop = () => { render(((performance.now() - start) / 1000) % timing.duration); requestAnimationFrame(loop); }; loop(); }
}
boot().catch(error => { console.error(error); window.__error = String(error && error.stack || error); });
})();
