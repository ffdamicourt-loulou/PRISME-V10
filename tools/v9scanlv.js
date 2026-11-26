#!/usr/bin/env node
// v9scanlv.js — scan fin des blancs région LV/EE/RU (bloc concernés + bbox-filter)
'use strict';
const fs = require('fs'), zlib = require('zlib');
const V9 = '/home/user/artifacts/v9';
const ylat = y => Math.atan(Math.sinh(y * Math.PI / 180)) * 180 / Math.PI;
const ISOS = ['LV', 'EE', 'RU', 'BY', 'LT', 'PL', 'FI'];
const blocks = {};
for (const iso of ISOS) {
  const b = JSON.parse(zlib.gunzipSync(fs.readFileSync(V9 + '/out/final/' + iso + '.json.gz')).toString());
  blocks[iso] = b.ps.map(d => d.slice(1).split('L').map(s => s.split(' ').map(Number))
    .map(([x, y]) => [x, ylat(y)]))
    .map(r => ({ r, x0: Math.min(...r.map(p => p[0])), x1: Math.max(...r.map(p => p[0])), y0: Math.min(...r.map(p => p[1])), y1: Math.max(...r.map(p => p[1])) }));
}
function any(x, y) {
  for (const iso of ISOS) for (const { r, x0, x1, y0, y1 } of blocks[iso]) {
    if (x < x0 || x > x1 || y < y0 || y > y1) continue;
    let w = 0; const n = r.length;
    for (let i = 0; i < n; i++) { const a = r[i], b = r[(i + 1) % n];
      if (a[1] <= y) { if (b[1] > y && (b[0] - a[0]) * (y - a[1]) - (x - a[0]) * (b[1] - a[1]) > 0) w++; }
      else if (b[1] <= y && (b[0] - a[0]) * (y - a[1]) - (x - a[0]) * (b[1] - a[1]) < 0) w--; }
    if (w !== 0) return iso;
  }
  return null;
}
// scan 0.02°
const whites = [];
const X0 = 21.0, X1 = 30.0, L0 = 56.0, L1 = 59.55;
for (let lat = L0; lat < L1; lat += 0.02)
  for (let lon = X0; lon < X1; lon += 0.02)
    if (!any(+lon.toFixed(3), +lat.toFixed(3))) whites.push([+lon.toFixed(3), +lat.toFixed(3)]);
console.log('cellules blanches 0.02°:', whites.length);
// clusters par cellule 0.2°
const cl = new Map();
for (const [x, y] of whites) { const k = (Math.floor(y * 5) / 5).toFixed(1) + '|' + (Math.floor(x * 5) / 5).toFixed(1); if (!cl.has(k)) cl.set(k, []); cl.get(k).push([x, y]); }
const arr = [...cl.entries()].sort((a, b) => b[1].length - a[1].length);
for (const [k, v] of arr.slice(0, 50)) console.log('cluster', k, 'n=', v.length, 'ex:', v.slice(0, 3).map(p => p.join(',')).join(' ; '));
