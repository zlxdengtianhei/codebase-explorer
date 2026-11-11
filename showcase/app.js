/* Codebase Explorer: code map.
 *
 * Reads data/<name>.json (made by prepare_data.py from a CBE catalog.json) and draws it on one canvas.
 *   ?mode=play      scripted 32 s film on a virtual clock: window.__render(t) draws the frame for time t
 *   (default)       interactive map: hover a unit, click a module or a unit
 * Layouts are computed once with d3-force (fixed start, fixed tick counts), so a frame depends only on t.
 */
(() => {
'use strict';

// ---------- constants -------------------------------------------------------------------------
const W = 1280, H = 720, T_TOTAL = 35;
const FULL = { x0: 44, y0: 122, x1: 1236, y1: 628 };      // stages 1-3: whole map
const R4 = { x0: 488, y0: 122, x1: 1238, y1: 634 };       // stage 4: map beside the tree
const ZONE5 = { x0: 456, y0: 124, x1: 796, y1: 600 };     // zoom target between tree and panel
const MAX_BIG_LABELS = 24, SIDEBAR_W = 440, PANEL_X = 806, PANEL_W = 456;
const HUES = [172, 38, 262, 350, 205, 98, 300, 60];
const C = { ink: '#e8f1ff', muted: '#9fb6cc', dim: '#6f8aa3', teal: '#6ee7d0', bg: '#06101b', neutral: [143, 180, 214] };
const LABEL_W = 170, BIG_FONT = 20, BIG_LH = 23, R3 = 0.8;               // R3: dot size in the system scene relative to the module scene
const SANS = '"IBM Plex Sans", system-ui, sans-serif', MONO = '"IBM Plex Mono", ui-monospace, monospace';

const qs = new URLSearchParams(location.search);
const requestedMode = qs.get('mode');
const MODE = requestedMode === 'play' || requestedMode === 'tour' ? requestedMode : 'interactive';
const RECORD = qs.has('record');
const DATA = qs.get('data') || 'cjson';
const LANG = qs.get('lang') || 'en';
document.body.classList.add(MODE);

const cv = document.getElementById('c');
const ctx = cv.getContext('2d');

// ---------- small helpers ---------------------------------------------------------------------
const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const lerp = (a, b, t) => a + (b - a) * t;
const prog = (t, a, b) => clamp((t - a) / (b - a));
const easeIO = t => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const easeOut = t => 1 - Math.pow(1 - t, 3);
function hash01(s) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return ((h >>> 0) % 100000) / 100000;
}
const hsl = (h, s, l, a = 1) => `hsla(${h},${s}%,${l}%,${a})`;
function mixRGB(a, b, t) { return [lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)]; }
function hslToRgb(h, s, l) {
  s /= 100; l /= 100;
  const k = n => (n + h / 30) % 12, a = s * Math.min(l, 1 - l);
  const f = n => l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)));
  return [f(0) * 255, f(8) * 255, f(4) * 255];
}
const rgba = (c, a) => `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${a})`;

const measureCache = new Map();
function tw(text, font) {
  const k = font + '|' + text;
  let v = measureCache.get(k);
  if (v === undefined) { ctx.font = font; v = ctx.measureText(text).width; measureCache.set(k, v); }
  return v;
}
function wrap(text, font, maxW, maxLines = 99, wordBoundary = false) {
  const words = text.split(/\s+/).filter(Boolean), lines = [];
  let cur = '';
  for (const w of words) {
    const trial = cur ? cur + ' ' + w : w;
    if (tw(trial, font) <= maxW || !cur) cur = trial;
    else { lines.push(cur); cur = w; }
  }
  if (cur) lines.push(cur);
  if (lines.length > maxLines) {
    const kept = lines.slice(0, maxLines);
    const rest = kept[maxLines - 1] + ' ' + lines[maxLines];
    kept[maxLines - 1] = wordBoundary ? fitWords(rest, font, maxW) : fit(rest, font, maxW, true);
    return kept;
  }
  return lines;
}
function fitWords(s, font, maxW) {           // clip at a word boundary with an ellipsis
  const words = s.trim().split(/\s+/);
  while (words.length > 1 && tw(words.join(' ') + '…', font) > maxW) words.pop();
  const stem = words.join(' ').trimEnd();
  return tw(stem + '…', font) <= maxW ? stem + '…' : fit(stem, font, maxW, true);
}
function fit(s, font, maxW, force) {         // clip to width with an ellipsis
  if (!force && tw(s, font) <= maxW) return s;
  while (s.length > 1 && tw(s + '…', font) > maxW) s = s.slice(0, -1);
  return s.trimEnd() + '…';
}
function rrect(x, y, w, h, r) { ctx.beginPath(); ctx.roundRect(x, y, w, h, r); }
function text(s, x, y, font, color, align = 'left', alpha = 1) {
  if (alpha <= 0.003) return;
  ctx.globalAlpha = alpha; ctx.font = font; ctx.fillStyle = color; ctx.textAlign = align; ctx.textBaseline = 'alphabetic';
  ctx.fillText(s, x, y); ctx.globalAlpha = 1;
}
function haloText(s, x, y, font, color, align = 'center', alpha = 1) {
  if (alpha <= 0.003) return;
  ctx.globalAlpha = alpha; ctx.font = font; ctx.textAlign = align; ctx.textBaseline = 'alphabetic';
  ctx.lineJoin = 'round'; ctx.lineWidth = 6; ctx.strokeStyle = 'rgba(5,12,21,0.9)'; ctx.strokeText(s, x, y);
  ctx.fillStyle = color; ctx.fillText(s, x, y); ctx.globalAlpha = 1;
}

// ---------- layout ----------------------------------------------------------------------------
function simulate(nodes, forces, ticks) {
  const sim = d3.forceSimulation(nodes).stop().alphaDecay(1 - Math.pow(0.001, 1 / ticks));
  for (const k of Object.keys(forces)) sim.force(k, forces[k]);
  for (let i = 0; i < ticks; i++) sim.tick();
}
function makeBox(nodes, boxOf) {
  return () => {
    for (const n of nodes) {
      const b = boxOf(n), p = n.r + 2;
      n.x = clamp(n.x, b.x0 + p, b.x1 - p); n.y = clamp(n.y, b.y0 + p, b.y1 - p);
    }
  };
}
function treemap(weights, rect, verticalFirst = false) {            // balanced binary slicing; weights must be sorted descending
  const out = new Array(weights.length);
  (function rec(idx, r, first) {
    if (idx.length <= 1) { if (idx.length) out[idx[0]] = r; return; }
    const total = idx.reduce((s, i) => s + weights[i], 0);
    let acc = 0, split = 1;
    for (let k = 0; k < idx.length - 1; k++) { acc += weights[idx[k]]; split = k + 1; if (acc >= total / 2) break; }
    const a = idx.slice(0, split), b = idx.slice(split);
    const fa = a.reduce((s, i) => s + weights[i], 0) / total;
    const horiz = first && verticalFirst ? false : r.w >= r.h;
    if (horiz) { rec(a, { x: r.x, y: r.y, w: r.w * fa, h: r.h }); rec(b, { x: r.x + r.w * fa, y: r.y, w: r.w * (1 - fa), h: r.h }); }
    else { rec(a, { x: r.x, y: r.y, w: r.w, h: r.h * fa }); rec(b, { x: r.x, y: r.y + r.h * fa, w: r.w, h: r.h * (1 - fa) }); }
  })(weights.map((_, i) => i), rect, true);
  return out;
}
const inset = (r, l, t, rr, b) => ({ x: r.x + l, y: r.y + t, w: r.w - l - rr, h: r.h - t - b });


function rectCollide(nodes, iters = 4) {      // nodes carry hw (half width), up/dn (extent above/below the anchor)
  return () => {
    for (let it = 0; it < iters; it++) for (let a = 0; a < nodes.length; a++) for (let b = a + 1; b < nodes.length; b++) {
      const p = nodes[a], q = nodes[b];
      const pc = p.y + (p.dn - p.up) / 2, qc = q.y + (q.dn - q.up) / 2, ph = (p.up + p.dn) / 2, qh = (q.up + q.dn) / 2;
      const dx = q.x - p.x, dy = qc - pc, ox = p.hw + q.hw - Math.abs(dx), oy = ph + qh - Math.abs(dy);
      if (ox > 0 && oy > 0) {
        if (ox < oy) { const m = (dx >= 0 ? 1 : -1) * ox / 2; p.x -= m; q.x += m; }
        else { const m = (dy >= 0 ? 1 : -1) * oy / 2; p.y -= m; q.y += m; }
      }
    }
  };
}
// anchors for groups of units: small force run (links = calls between groups), rectangles do not overlap
function groupLayout(groups, pos, pairs, box, size) {
  const of = new Map(); groups.forEach((g, gi) => g.forEach(i => of.set(i, gi)));
  const nodes = groups.map((g, gi) => {
    let x = 0, y = 0; for (const i of g) { x += pos[i][0]; y += pos[i][1]; }
    return { i: gi, x: x / g.length, y: y / g.length, c0: [x / g.length, y / g.length], ...size(g, gi) };
  });
  const wmap = new Map();
  for (const [a, b, c] of pairs) {
    const ga = of.get(a), gb = of.get(b);
    if (ga != null && gb != null && ga !== gb) { const key = ga < gb ? ga + ',' + gb : gb + ',' + ga; wmap.set(key, (wmap.get(key) || 0) + c); }
  }
  const links = [...wmap].map(([key, w]) => { const [a, b] = key.split(',').map(Number); return { source: a, target: b, w }; });
  simulate(nodes, {
    link: d3.forceLink(links).id(d => d.i).distance(d => d.source.hw + d.target.hw + 10).strength(d => Math.min(0.2, d.w / 60)),
    charge: d3.forceManyBody().strength(-240),
    x: d3.forceX(d => d.c0[0]).strength(0.05), y: d3.forceY(d => d.c0[1]).strength(0.05),
    rect: rectCollide(nodes, 4),
    box: () => { for (const d of nodes) { d.x = clamp(d.x, box.x0 + d.hw, box.x1 - d.hw); d.y = clamp(d.y, box.y0 + d.up, box.y1 - d.dn); } },
  }, 400);
  const rc = rectCollide(nodes, 1);             // final relaxation: only "do not overlap" and "stay in the box"
  const overlap = () => {
    let worst = 0;
    for (let a = 0; a < nodes.length; a++) for (let b = a + 1; b < nodes.length; b++) {
      const p = nodes[a], q = nodes[b];
      const ox = p.hw + q.hw - Math.abs(q.x - p.x), oy = (p.up + p.dn) / 2 + (q.up + q.dn) / 2 - Math.abs((q.y + (q.dn - q.up) / 2) - (p.y + (p.dn - p.up) / 2));
      if (ox > 0 && oy > 0) worst = Math.max(worst, Math.min(ox, oy));
    }
    return worst;
  };
  for (let round = 0; round < 8; round++) {    // if the boxes do not fit, shrink them a little and relax again
    for (let k = 0; k < 400; k++) {
      rc();
      for (const d of nodes) { d.x = clamp(d.x, box.x0 + d.hw, box.x1 - d.hw); d.y = clamp(d.y, box.y0 + d.up, box.y1 - d.dn); }
    }
    if (overlap() < 0.5) break;
    for (const d of nodes) { d.hw *= 0.95; d.up *= 0.96; d.dn *= 0.96; }
  }
  return { nodes, of, overlap: overlap() };
}

function buildModel(data, sub) {
  const units = data.units, n = units.length, files = data.files;
  const rs = n > 250 ? 0.74 : n < 150 ? 1.3 : 1;
  const rad = units.map(u => clamp(2.4 + 0.62 * Math.sqrt(u.nl), 3, 13) * rs);
  const deg = new Array(n).fill(0);
  for (const [a, b] of data.pairs) { deg[a]++; deg[b]++; }

  // ---- tree: modules (nodes that own units) grouped into tops. The page never clusters on its own.
  const byId = Object.fromEntries(data.nodes.map(x => [x.id, x]));
  const treeOk = data.nodes.length > 0 && units.every(u => byId[u.node]);
  let tops = [], mods = [], modOf = new Array(n).fill(-1), topRects = [], cells = [];
  if (treeOk) {
    const topW = {};
    for (const nd of data.nodes) if (nd.units.length) topW[nd.top] = (topW[nd.top] || 0) + nd.units.length;
    const topIds = Object.keys(topW).sort((a, b) => topW[b] - topW[a] || (a < b ? -1 : 1));
    tops = topIds.map((id, k) => ({ id, k, node: byId[id], hue: HUES[k % HUES.length], weight: topW[id], mods: [] }));
    const topIdx = Object.fromEntries(tops.map(t => [t.id, t.k]));
    const ownNodes = data.nodes.filter(nd => nd.units.length).sort((a, b) => (topIdx[a.top] - topIdx[b.top]) || (a.id < b.id ? -1 : 1));
    mods = ownNodes.map((nd, mi) => ({ mi, id: nd.id, node: nd, top: topIdx[nd.top], units: nd.units, label: nd.title, own: nd.id === nd.top }));
    for (const m of mods) { tops[m.top].mods.push(m.mi); for (const u of m.units) modOf[u] = m.mi; }
    for (const t of tops) {
      t.mods.forEach((mi, j) => {
        const L = t.mods.length === 1 ? 64 : 54 + 20 * j / (t.mods.length - 1);
        mods[mi].hue = t.hue; mods[mi].rgb = hslToRgb(t.hue, 66, L); mods[mi].css = hsl(t.hue, 66, L); mods[mi].cssLight = hsl(t.hue, 70, Math.min(82, L + 12));
      });
    }
    // the biggest modules get a title in the module scene; the rest only on hover
    const bySize = mods.map(m => m.mi).sort((a, b) => mods[b].units.length - mods[a].units.length || a - b);
    bySize.slice(0, MAX_BIG_LABELS).sort((a, b) => a - b).forEach((mi, k) => { mods[mi].big = k + 1; });
  }

  // ---- L0: one column per file (several rows when there are many files), units placed by line number
  const nf = files.length, maxL = Math.max(...files.map(f => f.nlines), 1);
  const single = nf <= 8, usableW = FULL.x1 - FULL.x0 - 60;
  const perRow = single ? nf : Math.min(nf, Math.max(8, Math.floor(usableW / 62)));
  const nrows = Math.ceil(nf / perRow), per = Math.ceil(nf / nrows);
  const labelH = single ? 40 : 6, rowH = (FULL.y1 - FULL.y0 - 8) / nrows;
  const cx0 = FULL.x0 + 70, cx1 = FULL.x1 - 70;
  const cols = files.map((f, i) => {
    const r = Math.floor(i / per), k = i % per, inRow = Math.min(per, nf - r * per);
    let cx, w;
    if (single) { cx = nf === 1 ? (FULL.x0 + FULL.x1) / 2 : cx0 + (cx1 - cx0) * (k + 0.5) / nf; w = Math.min(130, (cx1 - cx0) / nf * 0.8); }
    else { const slot = usableW / per; cx = FULL.x0 + 30 + (usableW - slot * inRow) / 2 + slot * (k + 0.5); w = Math.min(130, slot * 0.82); }
    const top = FULL.y0 + r * rowH + labelH;
    const hmax = single ? 420 : rowH - labelH - 16;
    const h = Math.max(single ? 70 : 24, hmax * Math.pow(f.nlines / maxL, 0.6));
    return { cx, w, top, h, path: f.path, nlines: f.nlines };
  });
  const nodes0 = units.map((u, i) => {
    const c = cols[u.file];
    return { i, r: rad[i], x: c.cx + (hash01(u.id) - 0.5) * c.w * 0.6, y: c.top + (u.l1 - 1) / c.nlines * c.h, tx: c.cx, ty: c.top + (u.l1 - 1) / c.nlines * c.h, col: c };
  });
  simulate(nodes0, {
    x: d3.forceX(d => d.tx).strength(0.22), y: d3.forceY(d => d.ty).strength(0.7),
    collide: d3.forceCollide(d => d.r + 1.2).iterations(2),
    box: makeBox(nodes0, d => ({ x0: d.col.cx - d.col.w / 2, x1: d.col.cx + d.col.w / 2, y0: d.col.top - 4, y1: d.col.top + d.col.h + 12 })),
  }, 220);
  const L0 = nodes0.map(d => [d.x, d.y]);

  // ---- L1: the units gather into CBE's own modules (nodes that own units); calls only pull inside the groups
  const links = data.pairs.map(([a, b]) => ({ source: a, target: b }));
  const nodes1 = units.map((u, i) => ({ i, r: rad[i], x: L0[i][0], y: L0[i][1] }));
  if (treeOk) {
    const g1 = groupLayout(mods.map(m => m.units), L0, data.pairs, FULL, (g, gi) => {
      const R = 8 + 11.5 * Math.sqrt(g.length) * rs / 1.3, big = mods[gi].big;
      const ll = big ? wrap(mods[gi].label, `600 ${BIG_FONT}px ${SANS}`, LABEL_W, 3, true) : [];
      const lw = Math.max(0, ...ll.map(l => tw(l, `600 ${BIG_FONT}px ${SANS}`)));
      return { hw: Math.max(R + 8, lw / 2 + 3), up: R + 6, dn: R + 8 + (big ? 3 + ll.length * BIG_LH : 0) };
    });
    mods.forEach((m, mi) => { m.ax = g1.nodes[mi].x; m.ay = g1.nodes[mi].y; });
    simulate(nodes1, {
      link: d3.forceLink(links).id(d => d.i).distance(d => 10 + d.source.r + d.target.r).strength(0.04),
      x: d3.forceX(d => mods[modOf[d.i]].ax).strength(0.9), y: d3.forceY(d => mods[modOf[d.i]].ay).strength(0.9),
      collide: d3.forceCollide(d => d.r + 2).iterations(3),
      box: makeBox(nodes1, () => FULL),
    }, 360);
  } else {                                     // no usable tree: plain call layout, no grouping
    const cxF = (FULL.x0 + FULL.x1) / 2, cyF = (FULL.y0 + FULL.y1) / 2;
    simulate(nodes1, {
      link: d3.forceLink(links).id(d => d.i).distance(d => 12 + d.source.r + d.target.r).strength(0.55),
      charge: d3.forceManyBody().strength(d => -14 - d.r * 1.2).distanceMax(220),
      collide: d3.forceCollide(d => d.r + 2.2).iterations(2),
      x: d3.forceX(cxF).strength(d => (deg[d.i] ? 0.035 : 0.12)), y: d3.forceY(cyF).strength(d => (deg[d.i] ? 0.06 : 0.2)),
      box: makeBox(nodes1, () => FULL),
    }, 460);
    fitTo(nodes1, FULL);
  }
  const L1 = nodes1.map(d => [d.x, d.y]);
  let L3 = L1;

  if (treeOk) {
    // L3: tops as blocks (treemap), modules inside, units inside their cell; selected leaf titles sit in a reserved strip
    // space each module needs in the system scene: its circle plus room for a possible two-line title
    for (const m of mods) {
      const R = (8 + 11.5 * Math.sqrt(m.units.length) * rs / 1.3) * R3 * 0.9, D = 2 * R + 14;
      m.demand = D * (D + 44);
    }
    topRects = treemap(tops.map(t => t.mods.reduce((a, mi) => a + mods[mi].demand, 0) * 1.2 + (t.mods.length === 1 ? 30000 : 16000)), { x: R4.x0, y: R4.y0, w: R4.x1 - R4.x0, h: R4.y1 - R4.y0 }, tops.length <= 3).map(r => inset(r, 4, 4, 4, 4));
    const target = new Array(mods.length), cellOf = new Array(mods.length);
    tops.forEach((t, k) => {
      for (const [px, nl] of [[26, 2], [22, 2], [22, 3], [19, 3]]) {   // narrow block: smaller title, more lines, then clipped
        t.tfont = `600 ${px}px ${SANS}`; t.tlh = px + 4;
        t.titleLines = wrap(t.node.title, t.tfont, topRects[k].w - 24, nl);
        if (t.titleLines.join(' ') === t.node.title && t.titleLines.every(l => tw(l, t.tfont) <= topRects[k].w - 20)) break;
      }
      t.titleLines = t.titleLines.map(l => fit(l, t.tfont, topRects[k].w - 20));
      t.hdr = 12 + t.titleLines.length * t.tlh;
      const hasLeaves = t.mods.some(mi => !mods[mi].own);
      const inner = inset(topRects[k], 6, t.hdr, 6, hasLeaves ? 50 : 6);
      const ids = t.mods.slice().sort((a, b) => mods[b].units.length - mods[a].units.length || a - b);
      const rects = treemap(ids.map(m => mods[m].demand), inner);
      ids.forEach((mi, j) => {
        const c = inset(rects[j], 2, 2, 2, 2);
        const lab = c.h > 74 && c.w >= 70 ? 42 : 0;
        cellOf[mi] = { ...c, lab }; target[mi] = [c.x + c.w / 2, c.y + (c.h - lab) / 2];
      });
    });
    cells = cellOf;
    // In the system scene, label only the largest leaf cell in each top-level block.
    // Keep a label only when the complete catalog title fits in two lines at 16 px or larger.
    tops.forEach(t => {
      const candidates = t.mods.filter(mi => !mods[mi].own && cellOf[mi])
        .sort((a, b) => cellOf[b].w * cellOf[b].h - cellOf[a].w * cellOf[a].h || a - b);
      let labelled = 0;
      for (const mi of candidates) {
        if (labelled >= 1) break;
        const m = mods[mi], maxW = Math.min(220, Math.max(180, topRects[t.k].w - 16));
        for (const px of [18, 17, 16]) {
          const font = `400 ${px}px ${SANS}`, lines = wrap(m.label, font, maxW, 2);
          if (lines.join(' ') !== m.label) continue;
          const r = topRects[t.k];
          m.systemLabel = { font, lines, lh: px + 2, x: r.x + r.w / 2, y: r.y + r.h - 30 };
          labelled++;
          break;
        }
      }
    });
    const nodes3 = units.map((u, i) => ({ i, r: rad[i], x: 0, y: 0, m: modOf[i] }));
    for (const d of nodes3) { d.x = R4.x0 + (L1[d.i][0] - FULL.x0) / (FULL.x1 - FULL.x0) * (R4.x1 - R4.x0); d.y = R4.y0 + (L1[d.i][1] - FULL.y0) / (FULL.y1 - FULL.y0) * (R4.y1 - R4.y0); }
    simulate(nodes3, {
      x: d3.forceX(d => target[d.m][0]).strength(0.3), y: d3.forceY(d => target[d.m][1]).strength(0.3),
      collide: d3.forceCollide(d => d.r * R3 + 1.6).iterations(3),
      box: makeBox(nodes3, d => ({ x0: cellOf[d.m].x, x1: cellOf[d.m].x + cellOf[d.m].w, y0: cellOf[d.m].y, y1: cellOf[d.m].y + cellOf[d.m].h - cellOf[d.m].lab })),
    }, 300);
    L3 = nodes3.map(d => [d.x, d.y]);
  }
  const L2 = L1;                               // stage 3 colours the groups where stage 2 left them

  // ---- derived: rank for the pop-in order, edge batches, camera target, sidebar rows
  const order = units.map((u, i) => i).sort((a, b) => (units[a].file - units[b].file) || (units[a].l1 - units[b].l1));
  const rank01 = new Array(n); order.forEach((i, k) => { rank01[i] = n > 1 ? k / (n - 1) : 0; });
  const NB = 6, pairs = data.pairs.map(([a, b, c], k) => ({ a, b, c, batch: Math.min(NB - 1, Math.floor(k * NB / data.pairs.length)) }));
  const ua = units.map(u => hash01(u.id));

  const focusUnit = data.focus && data.focus.unit != null ? data.focus.unit : -1;
  const focusMod = treeOk && focusUnit >= 0 ? modOf[focusUnit] : -1;
  const model = { data, sub, units, rad, deg, cols, L: [L0, L1, L2, L3], treeOk, tops, mods, modOf, topRects, cells, rank01, pairs, NB, ua, focusUnit, focusMod, nf };
  model.callers = new Array(n).fill(0); for (const p of pairs) model.callers[p.b]++;
  model.cam = (mi) => camFor(model, mi);
  model.rows = treeOk ? buildRows(model) : [];
  return model;
}
function fitTo(nodes, box) {
  const x0 = Math.min(...nodes.map(d => d.x - d.r)), x1 = Math.max(...nodes.map(d => d.x + d.r));
  const y0 = Math.min(...nodes.map(d => d.y - d.r)), y1 = Math.max(...nodes.map(d => d.y + d.r));
  for (const d of nodes) {
    d.x = box.x0 + (d.x - x0) / Math.max(1, x1 - x0) * (box.x1 - box.x0);
    d.y = box.y0 + (d.y - y0) / Math.max(1, y1 - y0) * (box.y1 - box.y0);
  }
}
function camFor(M, mi) {                      // zoom camera for one module (world centre, scale, screen centre)
  const ids = M.mods[mi].units, L3 = M.L[3];
  let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
  for (const i of ids) { x0 = Math.min(x0, L3[i][0] - M.rad[i]); x1 = Math.max(x1, L3[i][0] + M.rad[i]); y0 = Math.min(y0, L3[i][1] - M.rad[i]); y1 = Math.max(y1, L3[i][1] + M.rad[i]); }
  const bw = Math.max(40, x1 - x0) + 24, bh = Math.max(40, y1 - y0) + 24;
  const zw = ZONE5.x1 - ZONE5.x0, zh = ZONE5.y1 - ZONE5.y0;
  return { wx: (x0 + x1) / 2, wy: (y0 + y1) / 2, s: Math.min(zw / bw, zh / bh, 4.2), sx: (ZONE5.x0 + ZONE5.x1) / 2, sy: (ZONE5.y0 + ZONE5.y1) / 2 };
}
function buildRows(M) {                       // left bar: project, tops (and their direct children) as far as they fit
  const nodes = Object.fromEntries(M.data.nodes.map(n => [n.id, n]));
  const root = M.data.roots.length === 1 ? nodes[M.data.roots[0]] : null;
  const tops = M.tops.filter(t => !(root && t.id === root.id));
  const wrapW = SIDEBAR_W - 40, LIMIT = 636;
  const subMods = id => { const out = []; M.mods.forEach(m => { let c = m.node; while (c) { if (c.id === id) { out.push(m.mi); break; } c = nodes[c.parent]; } }); return out; };
  for (const mode of ['kids', 'caps2', 'caps1', 'titles']) {
    const rows = []; let y = 136;
    for (const t of tops) {
      const tl = wrap(t.node.title, `600 22px ${SANS}`, SIDEBAR_W - 52, 2);
      const capN = mode === 'kids' || mode === 'caps2' ? 2 : mode === 'caps1' ? 1 : 0;
      const lines = capN ? wrap(t.node.capability, `400 20px ${SANS}`, wrapW, capN) : [];
      const y0 = y - 22, h = 4 + tl.length * 25 + lines.length * 21 + 3;
      rows.push({ kind: 'top', y, y0, y1: y0 + h, titleLines: tl, lines, hue: t.hue, subMods: t.mods }); y += h;
      if (mode === 'kids') for (const cid of t.node.children || []) {
        const c = nodes[cid]; if (!c) continue;
        const sm = subMods(cid); if (!sm.length) continue;
        rows.push({ kind: 'kid', y, y0: y - 19, y1: y + 7, title: c.title, css: M.mods[sm[0]].css, subMods: sm }); y += 25;
      }
      y += 4;
    }
    if (y <= LIMIT + 8 || mode === 'titles') { rows.mode = mode; return rows; }
  }
}

// ---------- scripted film ---------------------------------------------------------------------
function stateAt(M, T) {
  const END = T_TOTAL;
  const S = {
    T, play: true, appear: T, sweep: prog(T, 2.0, 3.9),
    move: [prog(T, 6.0, 10.2), 0, prog(T, 17.0, 19.4)],
    fileA: lerp(0.72, 1, prog(T, 0, 0.8)) * (1 - prog(T, 6.2, 7.6)),
    edgeT: T, edgeBase: [lerp(0.26, 0.08, prog(T, 12.5, 15)), lerp(0.26, 0.34, prog(T, 12.5, 15))],
    colorT: T, haloA: prog(T, 9.8, 10.8), labelT: T, labelOut: 1 - prog(T, 17.0, 17.4), smallA: prog(T, 18.9, 19.6), topA: prog(T, 18.6, 20.0),
    legendA: prog(T, 4.2, 5.0),
    sidebar: easeIO(prog(T, 17.8, 19.0)), rowsT: T - 18.4,
    zoom: easeIO(prog(T, 22.0, 23.3)) * (1 - easeIO(prog(T, 28.0, 29.2))),
    dimOthers: prog(T, 22.0, 23.0) * (1 - prog(T, 28.0, 28.8)),
    mapDim: prog(T, 28.3, 28.9) * (1 - prog(T, END - 0.8, END - 0.2)),
    panel: easeIO(prog(T, 22.0, 23.0)) * (1 - easeIO(prog(T, 28.0, 28.6))),
    capP: prog(T, 23.1, 24.0), nameP: prog(T, 24.0, 24.4), expP: prog(T, 24.4, 26.8), locP: prog(T, 27.0, 27.4),
    focusA: prog(T, 23.8, 24.3) * (1 - prog(T, END - 0.7, END - 0.3)),
    term: easeIO(prog(T, 28.1, 28.6)) * (1 - easeIO(prog(T, END - 0.8, END - 0.3))),
    fade: prog(T, END - 0.3, END),
    focusMod: M.focusMod, focusUnit: M.focusUnit, hover: -1, hoverRow: -1, stats: easeOut(prog(T, 0.2, 1.8)),
    stage: T < 4 ? 0 : T < 11 ? 1 : T < 17 ? 2 : T < 22 ? 3 : T < 28 ? 4 : 5,
    // terminal: the `cbe source` output is on screen from 31.55 s to 34.2 s (2.6 s) before the terminal leaves
    typed: [Math.max(0, (T - 28.6) * 60), Math.max(0, (T - 30.0) * 90)], termOut: [prog(T, 28.95, 29.3), prog(T, 31.25, 31.55)],
  };
  return S;
}

// A tour stretches the existing six scenes to the measured narration. Its state is still
// produced by stateAt; only the two additional overlays and the virtual clock differ.
function tourAt(M, timing, tour, t) {
  const items = timing.items;
  let ix = items.length - 1;
  for (let i = 0; i < items.length; i++) {
    const end = i + 1 < items.length ? items[i + 1].t0 : timing.duration;
    if (t >= items[i].t0 && t < end) { ix = i; break; }
  }
  const cue = items[ix], entry = tour.items[ix];
  const p = clamp((t - cue.t0) / Math.max(0.001, cue.t1 - cue.t0));
  const ranges = { code: [0, 3.999], edges: [4, 10.999], modules: [11, 16.999], system: [17, 21.999], read: [22, 27.999], ask: [28, 34.999] };
  let oldT = 0;
  if (entry.scene === 'system' && entry.focus) oldT = 21.9;
  else if (ranges[entry.scene]) oldT = lerp(ranges[entry.scene][0], ranges[entry.scene][1], p);
  const S = stateAt(M, oldT);
  S.fade = 0; S.tourT = t; S.tourCue = { ...cue, caption: entry.caption || entry.say };
  S.tourFocusTops = [];
  if (entry.scene === 'edges') S.counter = { value: tour.facts.symbols, label: 'symbols' };
  if (entry.focus) {
    const ids = Array.isArray(entry.focus) ? entry.focus : [entry.focus];
    const focused = ids[Math.min(ids.length - 1, Math.floor(p * ids.length))];
    S.tourFocusTops = [focused]; S.tourCard = focused;
    S.sidebar = 0; S.focusMod = -1; S.focusUnit = -1; S.zoom = 0; S.dimOthers = 0; S.panel = 0;
  }
  if (entry.scene === 'start') S.start = entry;
  return S;
}
function tourTopAlpha(M, S, mi) {
  if (!S.tourFocusTops || !S.tourFocusTops.length) return 1;
  return S.tourFocusTops.includes(M.tops[M.mods[mi].top].id) ? 1 : 0.35;
}

// ---------- rendering -------------------------------------------------------------------------
let bgCanvas = null;
function bgImage() {
  if (bgCanvas) return bgCanvas;
  bgCanvas = document.createElement('canvas'); bgCanvas.width = W; bgCanvas.height = H;
  const g = bgCanvas.getContext('2d');
  const lin = g.createLinearGradient(0, H, W, 0); lin.addColorStop(0, '#050d17'); lin.addColorStop(0.55, '#0a1b2c'); lin.addColorStop(1, '#16384d');
  g.fillStyle = lin; g.fillRect(0, 0, W, H);
  const rad = g.createRadialGradient(W * 0.86, 0, 0, W * 0.86, 0, 640); rad.addColorStop(0, 'rgba(60,150,170,0.20)'); rad.addColorStop(1, 'rgba(60,150,170,0)');
  g.fillStyle = rad; g.fillRect(0, 0, W, H);
  return bgCanvas;
}

let last = null;          // last frame's screen positions, for hit testing
function render(M, S) {
  const { units, L, rad } = M, n = units.length;
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.clearRect(0, 0, W, H);
  ctx.drawImage(bgImage(), 0, 0);
  if (S.start) { drawStartCard(S.start); drawSubtitle(M, S); return; }

  // camera: zoom about a world point to a screen point, in log scale
  const fm = S.focusMod >= 0 ? M.cam(S.focusMod) : null;
  const z = fm ? S.zoom : 0;
  const cs = fm ? Math.exp(lerp(0, Math.log(fm.s), z)) : 1;
  const cw = fm ? [lerp(W / 2, fm.wx, z), lerp(H / 2, fm.wy, z)] : [W / 2, H / 2];
  const sc = fm ? [lerp(W / 2, fm.sx, z), lerp(H / 2, fm.sy, z)] : [W / 2, H / 2];
  const tx = sc[0] - cw[0] * cs, ty = sc[1] - cw[1] * cs;
  const X = x => x * cs + tx, Y = y => y * cs + ty;

  // positions (world) by chained, staggered transitions
  const wx = new Float32Array(n), wy = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    let x = L[0][i][0], y = L[0][i][1];
    for (let k = 0; k < 3; k++) {
      const d = M.ua[i] * 0.35, e = easeIO(clamp((S.move[k] - d) / 0.65));
      x += (L[k + 1][i][0] - L[k][i][0]) * e; y += (L[k + 1][i][1] - L[k][i][1]) * e;
    }
    wx[i] = x; wy[i] = y;
  }
  const sx = new Float32Array(n), sy = new Float32Array(n), sr = new Float32Array(n);
  for (let i = 0; i < n; i++) { sx[i] = X(wx[i]); sy[i] = Y(wy[i]); sr[i] = rad[i] * lerp(1, R3, easeIO(S.move[2])) * (cs > 1 ? Math.pow(cs, 0.85) : 1); }
  last = { sx, sy, sr, n, S };

  const mapAlpha = 1 - 0.62 * S.mapDim;
  ctx.globalAlpha = mapAlpha;
  const haveTree = M.treeOk;
  const colorMix = m => (S.play ? easeOut(clamp((S.colorT - (11.0 + 0.055 * m)) / 1.0)) : 1);
  const colorOf = i => {
    const m = M.modOf[i];
    if (!haveTree || m < 0) return C.neutral;
    return mixRGB(C.neutral, M.mods[m].rgb, colorMix(m));
  };

  // stage 1: the file columns
  if (S.fileA > 0.01 && S.play) {
    for (const c of M.cols) {
      ctx.globalAlpha = S.fileA * 0.55 * mapAlpha;
      rrect(c.cx - c.w / 2 - 6, c.top - 14, c.w + 12, c.h + 34, 10);
      ctx.fillStyle = 'rgba(120,170,210,0.07)'; ctx.fill();
      ctx.strokeStyle = 'rgba(140,190,230,0.22)'; ctx.lineWidth = 1.2; ctx.stroke();
    }
    if (M.nf <= 8) for (const c of M.cols) {
      const f = c.path.split('/').pop();
      text(fit(f, `500 22px ${MONO}`, Math.max(120, c.w + 60)), c.cx, c.top - 26, `500 22px ${MONO}`, C.muted, 'center', S.fileA * mapAlpha);
    }
    ctx.globalAlpha = mapAlpha;
  }

  // stage 4: top blocks (static rectangles; units settle into them)
  if (haveTree && S.topA > 0.01 && z < 0.98) {
    const a = S.topA * (1 - z) * mapAlpha;
    M.tops.forEach((t, k) => {
      const r = M.topRects[k], focused = S.tourFocusTops && S.tourFocusTops.includes(t.id);
      const ta = a * (S.tourFocusTops && S.tourFocusTops.length && !focused ? 0.35 : 1);
      ctx.globalAlpha = ta;
      rrect(r.x, r.y, r.w, r.h, 18); ctx.fillStyle = hsl(t.hue, 60, 60, focused ? 0.14 : 0.07); ctx.fill();
      ctx.strokeStyle = hsl(t.hue, 65, 66, focused ? 0.95 : 0.5); ctx.lineWidth = focused ? 4 : 2; ctx.stroke();
      t.titleLines.forEach((ln, j) => text(ln, r.x + 10, r.y + 28 + j * t.tlh, t.tfont, hsl(t.hue, 75, 78), 'left', ta));
    });
    ctx.globalAlpha = mapAlpha;
  }

  // module halos
  const mc = [];
  if (haveTree) {
    M.mods.forEach((m, mi) => {
      let cx = 0, cy = 0; for (const i of m.units) { cx += sx[i]; cy += sy[i]; }
      cx /= m.units.length; cy /= m.units.length;
      let r = 0; for (const i of m.units) r = Math.max(r, Math.hypot(sx[i] - cx, sy[i] - cy) + sr[i]);
      mc[mi] = { cx, cy, r: r + 9 * Math.pow(cs, 0.6) };
      const dim = (mi === S.focusMod ? 1 : 1 - 0.93 * S.dimOthers) * tourTopAlpha(M, S, mi);
      const mv = S.play ? (S.move[2] < 0.5 ? 1 - prog(S.move[2], 0, 0.1) : prog(S.move[2], 0.9, 1)) : 1;   // units are mid-flight: no rings
      if (S.haloA > 0.01 && mv > 0.01) {
        ctx.globalAlpha = S.haloA * dim * mv * mapAlpha;
        ctx.beginPath(); ctx.arc(cx, cy, mc[mi].r, 0, 6.2832);
        const hc = mixRGB([143, 190, 225], m.rgb, colorMix(mi));
        ctx.fillStyle = rgba(hc, 0.09); ctx.fill(); ctx.strokeStyle = rgba(hc, 0.36); ctx.lineWidth = 1.5; ctx.stroke();
      }
    });
    ctx.globalAlpha = mapAlpha;
  }

  // edges
  const nodim = i => (haveTree && M.modOf[i] !== S.focusMod ? 1 - 0.93 * S.dimOthers : 1) * (haveTree ? tourTopAlpha(M, S, M.modOf[i]) : 1);
  ctx.lineCap = 'round';
  if (z > 0.3) { ctx.save(); ctx.beginPath(); ctx.rect(SIDEBAR_W, 112, PANEL_X - SIDEBAR_W, 528); ctx.clip(); }
  const inferred = M.data.edge_basis === 'inferred';
  ctx.setLineDash(inferred ? [6, 5] : []);
  for (let k = 0; k < M.pairs.length; k++) {
    const p = M.pairs[k];
    const tb = 4.2 + 0.46 * p.batch;
    let a;
    if (S.play) {
      if (S.edgeT < tb) continue;
      const intra = haveTree && M.modOf[p.a] === M.modOf[p.b];
      const base = intra ? S.edgeBase[1] : S.edgeBase[0];
      a = lerp(0.95, base, easeOut(clamp((S.edgeT - tb) / 0.9)));
    } else a = (haveTree && M.modOf[p.a] === M.modOf[p.b]) ? S.edgeBase[1] : S.edgeBase[0];
    if (a < 0.01) continue;
    const intraFocus = haveTree && M.modOf[p.a] === S.focusMod && M.modOf[p.b] === S.focusMod;
    const touchFocus = S.focusUnit >= 0 && (p.a === S.focusUnit || p.b === S.focusUnit);
    let al = a * Math.min(nodim(p.a), nodim(p.b));
    if (intraFocus) al = Math.max(al, lerp(a, 0.5, S.dimOthers));
    if (touchFocus && S.focusA > 0) al = Math.max(al, 0.9 * S.focusA * S.dimOthers);
    ctx.globalAlpha = al * mapAlpha;
    ctx.strokeStyle = touchFocus && S.focusA > 0 && S.dimOthers > 0.5 ? '#9ff5e6' : '#6ee7d0';
    ctx.lineWidth = (touchFocus ? 2.2 : 1.1) * Math.pow(cs, 0.5);
    ctx.beginPath(); ctx.moveTo(sx[p.a], sy[p.a]); ctx.lineTo(sx[p.b], sy[p.b]); ctx.stroke();
  }
  ctx.setLineDash([]);
  if (z > 0.3) ctx.restore();

  // units
  const sweepP = S.sweep * 1.12 - 0.06;
  for (let i = 0; i < n; i++) {
    let a = 1, r = sr[i];
    if (S.play) { const t0 = 0.25 + 1.5 * M.rank01[i]; const u = clamp((S.appear - t0) / 0.45); a = lerp(0.68, 1, easeOut(u)); r *= 0.4 + 0.6 * easeOut(u); }
    if (a <= 0.01) continue;
    let col = colorOf(i);
    let bump = 0;
    if (S.play && S.sweep > 0 && S.sweep < 1) { bump = Math.max(0, 1 - Math.abs(M.rank01[i] - sweepP) / 0.06); if (bump) { r *= 1 + 0.35 * bump; col = mixRGB(col, [180, 255, 240], bump * 0.8); } }
    ctx.globalAlpha = a * nodim(i) * mapAlpha * (haveTree && i !== S.focusUnit && z > 0.1 ? 1 : 1);
    ctx.beginPath(); ctx.arc(sx[i], sy[i], r, 0, 6.2832);
    ctx.fillStyle = rgba(col, 0.94); ctx.fill();
    if (r > 6) { ctx.strokeStyle = 'rgba(5,13,23,0.55)'; ctx.lineWidth = 1.5; ctx.stroke(); }
  }
  ctx.globalAlpha = 1;

  // module labels (screen space; hidden while zoomed). Module scene: titles of the biggest modules, right under the circle.
  // System scene: the largest leaf in each multi-module top gets a full title in its label strip.
  if (haveTree) {
    const lz = (1 - clamp(z * 2.2)) * (1 - 0.6 * S.mapDim);
    M.mods.forEach((m, mi) => {
      const c = mc[mi];
      if (m.big) {
        const a = (S.play ? prog(S.labelT, 12.3 + 0.1 * m.big, 13.0 + 0.1 * m.big) * S.labelOut : 0) * lz * tourTopAlpha(M, S, mi);
        if (a > 0.01) {
          const font = `600 ${BIG_FONT}px ${SANS}`, lines = wrap(m.label, font, LABEL_W, 3, true);
          let y = c.cy + c.r + 20;
          for (const ln of lines) { haloText(ln, c.cx, y, font, m.cssLight, 'center', a); y += BIG_LH; }
        }
      }
      const a2 = (S.play ? S.smallA : 1) * lz * tourTopAlpha(M, S, mi);
      if (a2 > 0.01 && m.systemLabel) {
        const { font, lines, lh, x, y: y0 } = m.systemLabel;
        let y = y0;
        for (const ln of lines) { haloText(ln, x, y, font, m.cssLight, 'center', a2); y += lh; }
      }
    });
  }

  // focus unit
  if (S.focusUnit >= 0 && S.focusA > 0.01) {
    const i = S.focusUnit, pulse = 0.5 + 0.5 * Math.sin((S.play ? S.T : performance.now() / 1000) * 5);
    const g = ctx.createRadialGradient(sx[i], sy[i], 0, sx[i], sy[i], sr[i] * 3.4);
    g.addColorStop(0, 'rgba(110,231,208,0.55)'); g.addColorStop(1, 'rgba(110,231,208,0)');
    ctx.globalAlpha = S.focusA * mapAlpha; ctx.fillStyle = g; ctx.beginPath(); ctx.arc(sx[i], sy[i], sr[i] * 3.4, 0, 6.2832); ctx.fill();
    ctx.beginPath(); ctx.arc(sx[i], sy[i], sr[i] + 4 + pulse * 2, 0, 6.2832); ctx.strokeStyle = '#9ff5e6'; ctx.lineWidth = 3; ctx.stroke();
    ctx.globalAlpha = 1;
    if (z > 0.5 && S.nameP > 0) haloText(units[i].name, sx[i], sy[i] - sr[i] - 14, `500 24px ${MONO}`, '#bffcf0', 'center', S.nameP * S.focusA * (z - 0.5) * 2 * (1 - S.mapDim));
  }
  // hover
  if (S.hover >= 0) {
    const i = S.hover;
    ctx.beginPath(); ctx.arc(sx[i], sy[i], sr[i] + 4, 0, 6.2832); ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 2; ctx.stroke();
  }
  ctx.globalAlpha = 1;

  drawSidebar(M, S);
  drawPanel(M, S);
  drawTerminal(M, S);
  if (S.tourCard) drawTourCard(M, S.tourCard);
  drawHeader(M, S);
  drawLegend(M, S);
  drawSubtitle(M, S);
  if (S.hover >= 0) drawTip(M, S, sx[S.hover], sy[S.hover]);
  if (S.fade > 0.003) { ctx.globalAlpha = S.fade; ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H); ctx.globalAlpha = 1; }
}

function fmtK(v) { return v >= 1000 ? (v / 1000).toFixed(1) + 'k' : String(v); }
function drawHeader(M, S) {
  const st = M.data.stats, s = S.play ? S.stats : 1, ui = M.sub.ui;
  text(M.data.name, 40, 62, `600 46px ${SANS}`, C.ink);
  const counter = S.counter || { value: st.units, label: ui.units };
  const parts = [`${st.files} ${ui.files}`, `${fmtK(Math.round(st.tokens * s))} ${ui.tokens}`, `${Math.round(counter.value * s)} ${counter.label}`];
  text(parts.join('  ·  '), 42, 98, `400 24px ${SANS}`, C.muted);
  // step indicator
  const steps = M.sub.steps, font = `400 22px ${SANS}`, fontB = `600 22px ${SANS}`, gap = 30;
  const widths = steps.map((s, i) => tw(s, i === S.stage ? fontB : font));
  let x = W - 40 - widths.reduce((a, b) => a + b, 0) - gap * (steps.length - 1);
  steps.forEach((s, i) => {
    const on = i === S.stage, past = i < S.stage;
    text(s, x, 52, on ? fontB : font, on ? C.teal : past ? C.muted : C.dim);
    if (on) { ctx.fillStyle = C.teal; ctx.fillRect(x, 62, widths[i], 3); }
    x += widths[i] + gap;
  });
}
function drawLegend(M, S) {
  const a = S.play ? S.legendA : 1;
  if (a <= 0.01 || !M.pairs.length) return;
  const inf = M.data.edge_basis === 'inferred', font = `400 22px ${SANS}`;
  const label = inf ? (M.sub.ui.inferred || 'inferred relations') : (M.sub.ui.calls || 'resolved calls');
  const w = tw(label, font), x1 = W - 40, x0 = x1 - w - 56;
  ctx.globalAlpha = a; ctx.strokeStyle = '#6ee7d0'; ctx.lineWidth = 2; ctx.setLineDash(inf ? [6, 5] : []);
  ctx.beginPath(); ctx.moveTo(x0, 90); ctx.lineTo(x0 + 44, 90); ctx.stroke(); ctx.setLineDash([]); ctx.globalAlpha = 1;
  text(label, x1, 98, font, C.muted, 'right', a);
}
function drawSubtitle(M, S) {
  if (!S.play) return;
  if (S.tourCue) { drawTourSubtitle(S); return; }
  const cue = M.sub.cues.find(c => S.T >= c.t0 && S.T < c.t1);
  if (!cue) return;
  const a = Math.min(prog(S.T, cue.t0, cue.t0 + 0.3), 1 - prog(S.T, cue.t1 - 0.2, cue.t1));
  const font = `400 30px ${SANS}`, w = tw(cue.text, font), y = 685;
  ctx.globalAlpha = a * 0.78; rrect(W / 2 - w / 2 - 26, y - 38, w + 52, 56, 14); ctx.fillStyle = '#04090f'; ctx.fill(); ctx.globalAlpha = 1;
  text(cue.text, W / 2, y, font, '#f2f7ff', 'center', a);
}
function tourCaptionSegments(cue) {
  const font = `400 28px ${SANS}`, maxW = 1160;
  const sentences = (cue.caption.match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [cue.caption]).map(s => s.trim()).filter(Boolean);
  const parts = [];
  for (const sentence of sentences) {
    if (wrap(sentence, font, maxW).length <= 2) { parts.push(sentence); continue; }
    const stops = [];
    for (const m of sentence.matchAll(/[,;:]\s+/g)) stops.push(m.index + 1);
    const choices = stops.map(at => [sentence.slice(0, at).trim(), sentence.slice(at).trim()])
      .filter(parts => parts.every(part => wrap(part, font, maxW).length <= 2));
    choices.sort((a, b) => Math.abs(a[0].length - a[1].length) - Math.abs(b[0].length - b[1].length));
    parts.push(...(choices[0] || [sentence]));
  }
  const total = parts.reduce((n, part) => n + part.length, 0), duration = cue.t1 - cue.t0;
  let start = cue.t0;
  return parts.map((part, i) => {
    const end = i === parts.length - 1 ? cue.t1 : start + duration * part.length / total;
    const segment = { t0: start, t1: end, text: part, lines: wrap(part, font, maxW) };
    start = end;
    return segment;
  });
}
function drawTourSubtitle(S) {
  const cue = S.tourCue;
  if (S.tourT < cue.t0 || S.tourT >= cue.t1) return;
  const segments = tourCaptionSegments(cue), segment = segments.find(s => S.tourT >= s.t0 && S.tourT < s.t1);
  if (!segment) return;
  const font = `400 28px ${SANS}`, lines = segment.lines, lh = 36;
  const w = Math.max(...lines.map(line => tw(line, font))), bottom = 700, h = lines.length * lh + 20;
  ctx.globalAlpha = 0.86; rrect(W / 2 - w / 2 - 24, bottom - h, w + 48, h, 12); ctx.fillStyle = '#04090f'; ctx.fill(); ctx.globalAlpha = 1;
  lines.forEach((line, j) => text(line, W / 2, bottom - 14 - (lines.length - 1 - j) * lh, font, '#f2f7ff', 'center'));
}
function drawTourCard(M, id) {
  const node = M.data.nodes.find(n => n.id === id);
  if (!node) return;
  const x = 40, y = 142, w = 382, pad = 24;
  const titleFont = `600 27px ${SANS}`, capFont = `400 20px ${SANS}`;
  const titles = wrap(node.title, titleFont, w - 2 * pad), caps = wrap(node.capability, capFont, w - 2 * pad);
  const h = 32 + titles.length * 34 + 22 + caps.length * 27 + 24;
  ctx.fillStyle = 'rgba(4,12,21,0.96)'; rrect(x, y, w, h, 16); ctx.fill();
  ctx.strokeStyle = 'rgba(110,231,208,0.72)'; ctx.lineWidth = 2; ctx.stroke();
  let ty = y + 40;
  titles.forEach(line => { text(line, x + pad, ty, titleFont, C.ink); ty += 34; });
  ty += 14;
  caps.forEach(line => { text(line, x + pad, ty, capFont, C.muted); ty += 27; });
}
function drawStartCard(entry) {
  const x = 60, y = 172, w = 1160, h = 360;
  ctx.fillStyle = 'rgba(3,10,18,0.97)'; rrect(x, y, w, h, 22); ctx.fill();
  ctx.strokeStyle = 'rgba(110,231,208,0.65)'; ctx.lineWidth = 2; ctx.stroke();
  text('Map your own repository', W / 2, y + 70, `600 36px ${SANS}`, C.ink, 'center');
  text('Install', W / 2, y + 132, `400 22px ${SANS}`, C.muted, 'center');
  text(entry.install, W / 2, y + 178, `500 24px ${MONO}`, '#bffcf0', 'center');
  text('Repository', W / 2, y + 248, `400 22px ${SANS}`, C.muted, 'center');
  text(entry.repository, W / 2, y + 296, `500 26px ${MONO}`, C.teal, 'center');
}
function drawSidebar(M, S) {
  if (!M.treeOk || S.sidebar <= 0.003) return;
  const off = -SIDEBAR_W * (1 - S.sidebar);
  ctx.save(); ctx.translate(off, 0);
  ctx.fillStyle = 'rgba(5,14,24,0.90)'; ctx.fillRect(0, 112, SIDEBAR_W, 530);
  ctx.fillStyle = 'rgba(110,231,208,0.35)'; ctx.fillRect(SIDEBAR_W - 1, 112, 1, 530);
  M.rows.forEach((r, k) => {
    const a = S.play ? clamp((S.rowsT - 0.09 * k) / 0.4) : 1;
    if (a <= 0.01 || r.y > 650) return;
    const px = 22;
    const on = r.subMods && r.subMods.includes(S.focusMod) && S.focusA > 0 && S.dimOthers > 0.01;
    const hv = S.hoverRow === k;
    if (r.kind !== 'root' && (on || hv)) {
      ctx.globalAlpha = a * (on ? S.dimOthers : 1) * 0.9; ctx.fillStyle = 'rgba(110,231,208,0.14)';
      ctx.fillRect(4, r.y0, SIDEBAR_W - 10, r.y1 - r.y0); ctx.fillStyle = C.teal; ctx.fillRect(4, r.y0, 4, r.y1 - r.y0); ctx.globalAlpha = 1;
    }
    if (r.kind === 'root') {
      text(fit(r.title, `600 28px ${SANS}`, SIDEBAR_W - 44), px, r.y + 6, `600 28px ${SANS}`, C.ink, 'left', a);
    } else if (r.kind === 'top') {
      ctx.globalAlpha = a; ctx.fillStyle = hsl(r.hue, 70, 68); ctx.fillRect(px - 10, r.y0 + 6, 4, r.y1 - r.y0 - 12); ctx.globalAlpha = 1;
      r.titleLines.forEach((ln, j) => text(ln, px, r.y + j * 25, `600 22px ${SANS}`, hsl(r.hue, 78, 78), 'left', a));
      r.lines.forEach((ln, j) => text(ln, px, r.y + (r.titleLines.length - 1) * 25 + 22 + j * 21, `400 20px ${SANS}`, C.muted, 'left', a));
    } else {
      ctx.globalAlpha = a; ctx.beginPath(); ctx.arc(px + 22, r.y - 7, 6, 0, 6.2832); ctx.fillStyle = r.css; ctx.fill(); ctx.globalAlpha = 1;
      text(fit(r.title, `400 22px ${SANS}`, SIDEBAR_W - 90), px + 38, r.y, `400 22px ${SANS}`, on || hv ? '#ffffff' : C.ink, 'left', a);
    }
  });
  ctx.restore();
}
function panelText(M, S) {
  const mod = M.mods[S.focusMod], u = M.units[S.focusUnit];
  const cap = sentencesOf(mod.node.capability, 2);
  return { mod, u, cap };
}
function fitSentences(t, font, w, maxLines) {  // whole sentences only, as many as fit
  const parts = t.split(/(?<=[.!?])\s+(?=[A-Z])/);
  for (let k = parts.length; k > 1; k--) { const ln = wrap(parts.slice(0, k).join(' '), font, w); if (ln.length <= maxLines) return ln; }
  return wrap(parts[0], font, w, maxLines);
}
function sentencesOf(t, k) { const p = t.split(/(?<=[.!?])\s+(?=[A-Z])/); return p.slice(0, k).join(' '); }
function drawPanel(M, S) {
  if (!M.treeOk || S.panel <= 0.003 || S.focusMod < 0) return;
  const { mod, u, cap } = panelText(M, S);
  const x = PANEL_X + (1 - S.panel) * (PANEL_W + 40), y = 112, h = 536, pad = 24, tw_ = PANEL_W - pad * 2;
  ctx.save(); ctx.translate(x - PANEL_X, 0);
  ctx.fillStyle = 'rgba(5,14,24,0.93)'; rrect(PANEL_X, y, PANEL_W, h, 16); ctx.fill();
  ctx.strokeStyle = rgba(mod.rgb, 0.7); ctx.lineWidth = 2; ctx.stroke();
  const topNode = M.tops[mod.top].node;
  let ty = y + 40;
  if (!mod.own) { text(fit(topNode.title + '  ›', `400 22px ${SANS}`, tw_), PANEL_X + pad, ty, `400 22px ${SANS}`, hsl(mod.hue, 60, 72)); ty += 38; }
  else ty += 6;
  const tfont = `600 28px ${SANS}`;
  for (const ln of wrap(mod.node.title, tfont, tw_, 2)) { text(ln, PANEL_X + pad, ty, tfont, mod.cssLight); ty += 34; }
  ty += 2;
  const cfont = `400 22px ${SANS}`, clines = wrap(cap, cfont, tw_, 5);
  clines.forEach((ln, j) => { const a = prog(S.capP * (clines.length + 1), j, j + 1); text(ln, PANEL_X + pad, ty + j * 28, cfont, C.muted, 'left', a); });
  ty += clines.length * 28 + 14;
  ctx.globalAlpha = S.nameP; ctx.fillStyle = 'rgba(159,245,230,0.35)'; ctx.fillRect(PANEL_X + pad, ty - 6, tw_, 1.5); ctx.globalAlpha = 1;
  ty += 30;
  text(fit(u.name, `500 26px ${MONO}`, tw_), PANEL_X + pad, ty, `500 26px ${MONO}`, '#bffcf0', 'left', S.nameP);
  ty += 12;
  const efont = `400 22px ${SANS}`, room = Math.floor((y + h - 78 - ty) / 28), elines = fitSentences(u.explain, efont, tw_, Math.max(3, room));
  let budget = Math.floor(S.expP * elines.join(' ').length);
  elines.forEach((ln, j) => {
    const part = ln.slice(0, Math.max(0, budget)); budget -= ln.length + 1;
    if (part) text(part, PANEL_X + pad, ty + 28 * (j + 1), efont, C.ink);
  });
  const ly = y + h - 28;
  text(u.loc, PANEL_X + pad, ly, `500 22px ${MONO}`, C.teal, 'left', S.locP);
  ctx.globalAlpha = S.locP; ctx.fillStyle = C.teal; ctx.fillRect(PANEL_X + pad, ly + 8, 36 + 0 * S.locP, 2); ctx.globalAlpha = 1;
  ctx.restore();
}
function drawTerminal(M, S) {
  const f = M.data.find;
  if (!f || S.term <= 0.003) return;
  if (M.treeOk && S.sidebar > 0.5) { ctx.globalAlpha = 0.72 * S.term; ctx.fillStyle = '#06101b'; ctx.fillRect(0, 112, SIDEBAR_W, 530); ctx.globalAlpha = 1; }
  const mono = `400 20px ${MONO}`, monoM = `500 20px ${MONO}`, lh = 27, pad = 24, CW = tw('M', mono);
  const x = 40, w = 1200, maxCh = Math.floor((w - pad * 2) / CW);
  const cmd1 = `cbe find ${f.term}`, cmd2 = `cbe source --id ${f.source.id}`;
  const cmdW = maxCh - 2;
  const chop = (str, n, lines) => { const out = []; for (let k = 0; k < str.length && out.length < lines; k += n) out.push(str.slice(k, k + n)); if (str.length > n * lines) out[lines - 1] = out[lines - 1].slice(0, -1) + '…'; return out; };
  // what the real commands printed (prepare_data.py ran them); older data falls back to the catalog row
  const findRaw = f.raw || `${f.hit.name} | ${f.hit.id} | | ${f.hit.loc} | ${f.hit.summary}`;
  const findLines = chop(findRaw, maxCh, 4);
  let srcLines;
  if (f.src_raw && f.src_raw.length) {
    const body = f.src_raw.slice(1), shown = body.slice(0, 5);
    srcLines = [f.src_raw[0], ...shown.map(l => (l.length > maxCh ? l.slice(0, maxCh - 1) + '…' : l))];
    if (body.length > shown.length) srcLines.push(`… ${body.length - shown.length} more lines`);
  } else srcLines = [`# ${f.source.loc}`, `${f.source.line}: ${f.source.sig}`];
  const commandLines = (str, n, lines) => {
    if (str.length <= n) return [str];
    const stops = [];
    for (let i = str.indexOf('::'); i >= 0; i = str.indexOf('::', i + 2)) stops.push(i + 2);
    stops.sort((a, b) => Math.abs(a - str.length / 2) - Math.abs(b - str.length / 2) || a - b);
    for (const stop of stops) {
      const first = str.slice(0, stop), second = str.slice(stop);
      if (first.length <= n && second.length <= n) return [first, second];
    }
    return chop(str, n, lines);
  };
  const c1 = commandLines(cmd1, cmdW, 3), c2 = commandLines(cmd2, cmdW, 3);
  const nLines = c1.length + findLines.length + c2.length + srcLines.length;
  const h = nLines * lh + 50;
  const top = lerp(H + 4, 640 - h, S.term);
  ctx.save();
  ctx.fillStyle = 'rgba(3,9,15,0.97)'; rrect(x, top, w, h, 14); ctx.fill();
  ctx.strokeStyle = 'rgba(110,231,208,0.55)'; ctx.lineWidth = 2; ctx.stroke();
  let ty = top + 40;
  const cursorOn = (Math.floor((S.play ? S.T : performance.now() / 1000) * 2.5) % 2) === 0;
  const typedCmd = (full, parts, n, y) => {         // typed text, wrapped over the lines of the command
    const shown = full.slice(0, Math.max(0, Math.floor(n))), promptX = x + pad + 2 * CW;
    text('$', x + pad, y, monoM, C.teal);
    let start = 0;
    parts.forEach((p, j) => { const seg = shown.slice(start, start + p.length); if (seg) text(seg, promptX, y + j * lh, mono, C.ink); start += p.length; });
    if (cursorOn && n > 0 && n < full.length + 1) {
      let offset = 0, j = 0;
      while (j < parts.length - 1 && shown.length > offset + parts[j].length) { offset += parts[j].length; j++; }
      const seg = shown.slice(offset, offset + parts[j].length);
      ctx.fillStyle = C.ink; ctx.fillRect(promptX + tw(seg, mono) + 2, y + j * lh - 17, 10, 20);
    }
  };
  typedCmd(cmd1, c1, S.typed[0], ty); ty += lh * c1.length;
  findLines.forEach((ln, j) => { text(ln, x + pad, ty, j === 0 ? monoM : mono, j === 0 ? '#bffcf0' : C.muted, 'left', S.termOut[0]); ty += lh; });
  if (S.typed[1] > 0) typedCmd(cmd2, c2, S.typed[1], ty);
  ty += lh * c2.length;
  srcLines.forEach((ln, j) => { text(ln, x + pad, ty, mono, j === 0 ? C.dim : (ln.startsWith('…') ? C.dim : C.ink), 'left', S.termOut[1]); ty += lh; });
  ctx.restore();
}
function drawTip(M, S, px, py) {
  const u = M.units[S.hover], font = `400 22px ${SANS}`, mono = `500 22px ${MONO}`;
  const lines = wrap(u.summary, font, 420, 4), wd = 456, h = 40 + lines.length * 28 + 34;
  const mod = M.treeOk && M.modOf[S.hover] >= 0 ? M.mods[M.modOf[S.hover]] : null;
  let x = clamp(px + 22, 8, W - wd - 8), y = clamp(py - h / 2, 112, H - h - 8);
  ctx.fillStyle = 'rgba(4,10,17,0.95)'; rrect(x, y, wd, h, 12); ctx.fill(); ctx.strokeStyle = 'rgba(110,231,208,0.6)'; ctx.lineWidth = 1.5; ctx.stroke();
  text(fit(u.name, mono, wd - 28), x + 14, y + 32, mono, '#bffcf0');
  lines.forEach((ln, j) => text(ln, x + 14, y + 62 + j * 28, font, C.ink));
  text(u.loc, x + 14, y + h - 12, `400 20px ${MONO}`, C.dim);
  if (mod) text(fit(mod.node.title, `600 20px ${SANS}`, wd - 28 - tw(u.loc, `400 20px ${MONO}`) - 14), x + wd - 14, y + h - 12, `600 20px ${SANS}`, mod.cssLight, 'right');
}

// ---------- interactive mode ------------------------------------------------------------------
function interactive(M) {
  const ui = { zoom: 0, zoomT: 0, focusMod: M.focusMod >= 0 ? M.focusMod : 0, focusUnit: M.focusUnit, hover: -1, hoverRow: -1, mx: -1, my: -1 };
  const pick = () => {
    if (!last || ui.mx < 0) return -1;
    let best = -1, bd = 1e9;
    for (let i = 0; i < last.n; i++) { const d = Math.hypot(last.sx[i] - ui.mx, last.sy[i] - ui.my); if (d < last.sr[i] + 6 && d < bd) { bd = d; best = i; } }
    return best;
  };
  const state = () => {
    const S = stateAt(M, 99); S.play = false;
    S.edgeBase = [0.09, 0.34]; S.labelOut = 0; S.smallA = 1; S.legendA = 1; S.haloA = 1; S.topA = 1; S.sidebar = 1; S.rowsT = 99; S.fade = 0; S.stage = ui.zoomT ? 4 : 3;
    S.zoom = ui.zoom; S.dimOthers = ui.zoom; S.panel = ui.zoom; S.capP = S.nameP = S.expP = S.locP = 1; S.focusA = ui.zoomT ? 1 : 0;
    S.focusMod = M.treeOk ? ui.focusMod : -1; S.focusUnit = ui.focusUnit; S.term = 0; S.mapDim = 0; S.hover = ui.hover; S.hoverRow = ui.hoverRow;
    return S;
  };
  const toCanvas = e => { const r = cv.getBoundingClientRect(); return [(e.clientX - r.left) * W / r.width, (e.clientY - r.top) * H / r.height]; };
  cv.addEventListener('mousemove', e => {
    [ui.mx, ui.my] = toCanvas(e); ui.hover = pick(); ui.hoverRow = rowAt(ui.mx, ui.my);
    cv.style.cursor = ui.hover >= 0 || ui.hoverRow >= 0 ? 'pointer' : 'default';
  });
  cv.addEventListener('mouseleave', () => { ui.mx = -1; ui.hover = -1; ui.hoverRow = -1; });
  const rowAt = (x, y) => { if (!M.treeOk || x > SIDEBAR_W) return -1; for (let k = 0; k < M.rows.length; k++) { const r = M.rows[k]; if (r.subMods && y > r.y0 && y < r.y1) return k; } return -1; };
  const openModule = (mi, unit) => {
    ui.focusMod = mi; ui.zoomT = 1;
    ui.focusUnit = unit != null ? unit : pickDefaultUnit(M, mi);
  };
  cv.addEventListener('click', e => {
    [ui.mx, ui.my] = toCanvas(e);
    const r = rowAt(ui.mx, ui.my); if (r >= 0) return openModule(M.rows[r].subMods.slice().sort((a, b) => M.mods[b].units.length - M.mods[a].units.length)[0]);
    const u = pick(); if (u >= 0 && M.treeOk && M.modOf[u] >= 0) return openModule(M.modOf[u], u);
    if (M.treeOk && ui.zoomT) { const S = last && last.S; ui.zoomT = 0; return; }
    if (M.treeOk && !ui.zoomT && last) { // click on a halo: open the nearest module
      let best = -1, bd = 1e9;
      M.mods.forEach((m, mi) => { let cx = 0, cy = 0; for (const i of m.units) { cx += last.sx[i]; cy += last.sy[i]; } cx /= m.units.length; cy /= m.units.length; const d = Math.hypot(cx - ui.mx, cy - ui.my); if (d < bd) { bd = d; best = mi; } });
      if (best >= 0 && bd < 80) openModule(best);
    }
  });
  addEventListener('keydown', e => { if (e.key === 'Escape') ui.zoomT = 0; });
  const loop = () => {
    ui.zoom += (ui.zoomT - ui.zoom) * 0.16; if (Math.abs(ui.zoom - ui.zoomT) < 0.002) ui.zoom = ui.zoomT;
    ui.hover = pick(); if (ui.zoom > 0.5) { /* hover works while zoomed too */ }
    render(M, state()); requestAnimationFrame(loop);
  };
  window.__ui = ui; window.__hoverUnit = i => { render(M, state()); const p = last; ui.mx = p.sx[i]; ui.my = p.sy[i]; ui.hover = i; render(M, state()); };
  window.__unitScreen = i => { render(M, state()); return [last.sx[i], last.sy[i]]; };
  window.__open = (mi, u) => { openModule(mi, u); ui.zoom = ui.zoomT; };
  requestAnimationFrame(loop);
}
function pickDefaultUnit(M, mi) {
  const ids = M.mods[mi].units.filter(i => M.units[i].sig);
  const pool = ids.length ? ids : M.mods[mi].units;
  return pool.slice().sort((a, b) => M.callers[b] - M.callers[a] || M.units[b].nl - M.units[a].nl)[0];
}

// ---------- boot ------------------------------------------------------------------------------
async function boot() {
  const fonts = [['IBM Plex Sans', 'IBMPlexSans-Regular.woff2', '400'], ['IBM Plex Sans', 'IBMPlexSans-SemiBold.woff2', '600'],
    ['IBM Plex Mono', 'IBMPlexMono-Regular.woff2', '400'], ['IBM Plex Mono', 'IBMPlexMono-Medium.woff2', '500']];
  await Promise.all(fonts.map(async ([fam, file, wt]) => { const ff = new FontFace(fam, `url(fonts/${file})`, { weight: wt }); await ff.load(); document.fonts.add(ff); }));
  const [data, sub] = await Promise.all([fetch(`data/${DATA}.json`).then(r => r.json()), fetch(`subtitles/${LANG}.json`).then(r => r.json())]);
  let timing = null, tour = null;
  if (MODE === 'tour') {
    [tour, timing] = await Promise.all([
      fetch(`tour/${DATA}.${LANG}.json`).then(r => r.json()),
      fetch(`tour/${DATA}.${LANG}.timing.json`).then(r => r.json()),
    ]);
  }
  const M = buildModel(data, sub), total = timing ? timing.duration : T_TOTAL;
  window.__model = M; window.__total = total;
  window.__render = t => { render(M, timing ? tourAt(M, timing, tour, t) : stateAt(M, t)); };
  window.__tourState = t => {
    if (!timing) return null;
    const S = tourAt(M, timing, tour, t);
    return { id: S.tourCue.id, focus: S.tourFocusTops, caption: S.tourCue.caption, scene: S.start ? 'start' : tour.items[timing.items.findIndex(c => c.id === S.tourCue.id)].scene };
  };
  window.__captionSegments = () => timing ? timing.items.flatMap((cue, i) => {
    const entry = tour.items[i], withCaption = { ...cue, caption: entry.caption || entry.say };
    return tourCaptionSegments(withCaption).map((s, j) => ({ id: cue.id, segment: j + 1, ...s, lines: s.lines.length }));
  }) : [];
  window.__ready = true;
  if (MODE === 'play' || MODE === 'tour') {
    if (!RECORD) { const t0 = performance.now(); const loop = () => { window.__render(((performance.now() - t0) / 1000) % total); requestAnimationFrame(loop); }; loop(); }
    else window.__render(0);
  } else interactive(M);
}
boot().catch(e => { console.error(e); window.__error = String(e && e.stack || e); });
})();
