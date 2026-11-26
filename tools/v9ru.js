#!/usr/bin/env node
// v9ru.js — Bloc RUSSIE niveau pays à partir des sujets fédéraux OSM
// (hyperknot/country-levels-export geojson/high/iso2/RU/, précision ~0.001°).
// 1) charge tous les sujets (data/RU-hk/*.geojson, sauf CR/SEV = Crimée);
// 2) DISSOUT les frontières internes par annulation d'arêtes (a->b vs b->a);
// 3) rechaîne les arêtes restantes en boucles;
// 4) clip à lon CUT (41.55) + fermeture le long du méridien;
// 5) projette Mercator degrés + écrit le bloc out/work/RU.json.gz.
'use strict';
const fs = require('fs'), zlib = require('zlib'), path = require('path');
const DIR = '/home/user/artifacts/v9/data/RU-hk';
const CUT = 41.55; // méridien de coupe (hors viewBox carte, X1=40.23)
const OUT = '/home/user/artifacts/v9/out/work/RU.json.gz';

// --- lecture des sujets ------------------------------------------------
const files = fs.readdirSync(DIR).filter(f => f.endsWith('.geojson')).sort();
const ringsAll = []; // [{code, ring:[[lon,lat],...]}]
let npts = 0;
for (const f of files) {
  const code = f.slice(3, 5);
  const g = JSON.parse(fs.readFileSync(path.join(DIR, f), 'utf8')).geometry;
  const polys = g.type === 'Polygon' ? [g.coordinates] : g.coordinates;
  for (const poly of polys) for (const ring of poly) {
    ringsAll.push({ code, ring });
    npts += ring.length;
  }
}
console.log('sujets:', files.length, 'anneaux:', ringsAll.length, 'pts:', npts);

// --- dissolution par annulation d'arêtes -------------------------------
// clé = A|B (A<B lexicographique); arêtes internes = paire a->b + b->a.
const edgeCount = new Map(); // key -> {dir: [arêtes a->b], rev: [arêtes b->a]}
const key = (a, b) => { const ka = a[0] + ',' + a[1], kb = b[0] + ',' + b[1]; return ka < kb ? ka + '|' + kb : kb + '|' + ka; };
let nEdges = 0, nCancel = 0;
for (const { code, ring } of ringsAll) {
  for (let i = 0; i < ring.length; i++) {
    const a = ring[i], b = ring[(i + 1) % ring.length];
    if (a[0] === b[0] && a[1] === b[1]) continue;
    const k = key(a, b);
    const fwd = (a[0] + ',' + a[1]) < (b[0] + ',' + b[1]);
    let e = edgeCount.get(k);
    if (!e) { e = { dir: [], rev: [] }; edgeCount.set(k, e); }
    (fwd ? e.dir : e.rev).push([a, b]);
    nEdges++;
  }
}
// arêtes externes = celles non annulées
const outer = []; // [a,b]
for (const [k, e] of edgeCount) {
  const m = Math.min(e.dir.length, e.rev.length);
  nCancel += m;
  for (let i = 0; i < e.dir.length - m; i++) outer.push(e.dir[i]);
  for (let i = 0; i < e.rev.length - m; i++) outer.push(e.rev[i]);
}
console.log('arêtes:', nEdges, 'annulées (internes):', 2 * nCancel, 'restantes:', outer.length);

// --- rechaînage en boucles ----------------------------------------------
const nodeOut = new Map(); // "lon,lat" -> [arêtes partant de ce nœud]
for (const [a, b] of outer) {
  const ka = a[0] + ',' + a[1];
  if (!nodeOut.has(ka)) nodeOut.set(ka, []);
  nodeOut.get(ka).push([a, b]);
}
const used = new Set();
const loops = [];
for (let i = 0; i < outer.length; i++) {
  const [a0, b0] = outer[i];
  const k0 = a0[0] + ',' + a0[1] + '>' + b0[0] + ',' + b0[1];
  if (used.has(k0)) continue;
  const chain = [a0]; let cur = b0;
  used.add(k0);
  let guard = 0;
  while (guard++ < 2000000) {
    const kc = cur[0] + ',' + cur[1];
    if (kc === a0[0] + ',' + a0[1]) break;
    const outs = nodeOut.get(kc) || [];
    let found = null;
    for (const [a, b] of outs) {
      const kk = a[0] + ',' + a[1] + '>' + b[0] + ',' + b[1];
      if (!used.has(kk)) { found = [a, b, kk]; break; }
    }
    if (!found) break;
    used.add(found[2]); chain.push(found[0]); cur = found[1];
  }
  const kc = cur[0] + ',' + cur[1];
  if (kc === a0[0] + ',' + a0[1] && chain.length >= 4) loops.push(chain);
}
console.log('boucles rechaînées:', loops.length, '(ouvertes non fermées:', outer.length - loops.reduce((s, l) => s + l.length, 0), 'arêtes orphelines)');

// --- clip au méridien CUT (Sutherland–Hodgman, demi-plan lon <= CUT) -----
function clipRing(ring) {
  const ins = (p) => p[0] <= CUT;
  const out = [];
  const n = ring.length;
  for (let i = 0; i < n; i++) {
    const p = ring[i], q = ring[(i + 1) % n];
    const pin = ins(p), qin = ins(q);
    if (pin && qin) out.push(q);
    else if (pin && !qin) {
      const t = (CUT - p[0]) / (q[0] - p[0]);
      out.push([CUT, +(p[1] + t * (q[1] - p[1])).toFixed(6)]);
    } else if (!pin && qin) {
      const t = (CUT - p[0]) / (q[0] - p[0]);
      out.push([CUT, +(p[1] + t * (q[1] - p[1])).toFixed(6)], q);
    }
  }
  if (out.length < 4) return [];
  // retire les doublons consécutifs éventuels sur la frontière de coupe
  const cl = [];
  for (const p of out) {
    const l = cl[cl.length - 1];
    if (!l || l[0] !== p[0] || l[1] !== p[1]) cl.push(p);
  }
  return cl.length >= 4 ? [cl] : [];
}
const clipped = [];
for (const loop of loops) for (const r of clipRing(loop)) {
const myd = (lat) => Math.asinh(Math.tan(lat * Math.PI / 180)) * 180 / Math.PI;
  // filtre terre François-Joseph (lat ~83°, merc-Y > 102.33) : détruirait le cadrage
  const maxY = Math.max(...r.map(p => myd(p[1])));
  if (maxY > 102.33) { console.log('anneau > 80°72N droppé (François-Joseph):', r.length, 'pts'); continue; }
  clipped.push(r);
}
console.log('boucles après clip', CUT, ':', clipped.length);

// --- projection + bloc -----------------------------------------------------
const myd2 = (lat) => Math.asinh(Math.tan(lat * Math.PI / 180)) * 180 / Math.PI;
const fmt = (x) => {
  const s = x.toFixed(5);
  return s.replace(/0+$/, '').replace(/\.$/, '');
};
let X0 = 1e9, Y0 = 1e9, X1 = -1e9, Y1 = -1e9, tot = 0;
const ps = [];
for (const r of clipped) {
  const xy = r.map(p => { const y = myd2(p[1]); X0 = Math.min(X0, p[0]); X1 = Math.max(X1, p[0]); Y0 = Math.min(Y0, y); Y1 = Math.max(Y1, y); return [p[0], y]; });
  if (xy.length < 4) continue;
  tot += xy.length;
  let d = 'M' + fmt(xy[0][0]) + ' ' + fmt(xy[0][1]);
  for (let i = 1; i < xy.length; i++) d += 'L' + fmt(xy[i][0]) + ' ' + fmt(xy[i][1]);
  ps.push(d);
}
const block = {
  iso: 'RU', nom: 'Россия', ps, b: [X0, Y0, X1, Y1],
  boucles: ps.length, ouvertes: 0, internes: 0, pts: tot
};
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, zlib.gzipSync(JSON.stringify(block)));
console.log('bloc écrit:', OUT, 'boucles:', ps.length, 'pts:', tot, 'bbox:', [X0, Y0, X1, Y1].map(v => v.toFixed(2)).join(' '));
