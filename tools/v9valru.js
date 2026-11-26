#!/usr/bin/env node
// v9valru.js — validation bloc RU + carte des blancs région baltique (41 blocs)
'use strict';
const fs = require('fs'), zlib = require('zlib');
const V9 = '/home/user/artifacts/v9';
const ylat = y => Math.atan(Math.sinh(y * Math.PI / 180)) * 180 / Math.PI;
function rings(iso) {
  const b = JSON.parse(zlib.gunzipSync(fs.readFileSync(V9 + '/out/final/' + iso + '.json.gz')).toString());
  return b.ps.map(d => d.slice(1).split('L').map(s => s.split(' ').map(Number)).map(([x, y]) => [x, ylat(y)]));
}
const blocks = {};
for (const f of fs.readdirSync(V9 + '/out/final')) {
  if (f.endsWith('.json.gz')) blocks[f.slice(0, 2)] = rings(f.slice(0, 2));
}
console.log('blocs chargés:', Object.keys(blocks).length);
function cov(iso, x, y) {
  for (const r of blocks[iso]) {
    let w = 0; const n = r.length;
    for (let i = 0; i < n; i++) { const a = r[i], b = r[(i + 1) % n];
      if (a[1] <= y) { if (b[1] > y && (b[0] - a[0]) * (y - a[1]) - (x - a[0]) * (b[1] - a[1]) > 0) w++; }
      else if (b[1] <= y && (b[0] - a[0]) * (y - a[1]) - (x - a[0]) * (b[1] - a[1]) < 0) w--; }
    if (w !== 0) return true;
  }
  return false;
}
function any(x, y) { for (const i in blocks) if (cov(i, x, y)) return i; return null; }
const probes = [
  ['Petchory', 27.55, 57.60, 'RU'], ['Pytalovo', 29.33, 57.02, 'RU'],
  ['StPetersbourg', 30.31, 59.94, 'RU'], ['Moscou', 37.62, 55.75, 'RU'],
  ['Mourmansk', 33.08, 68.97, 'RU'], ['Sotchi', 39.72, 43.4, 'RU'],
  ['Krasnodar', 38.98, 45.03, 'RU'], ['Ostrov', 28.35, 57.35, 'RU'],
  ['Sebezh', 28.47, 56.29, 'RU'], ['Opotchka? Zilupe', 28.14, 56.61, 'RU'],
  ['Zelenogradsk', 21.0117, 54.9578, 'RU'], ['Morskoe', 20.55, 54.96, 'RU'],
  ['KaliningradVille', 20.511, 54.71, 'RU'], ['Sovetsk', 22.53, 55.08, 'RU'],
  ['Baltiysk', 19.91, 54.65, 'RU'], ['Yantarny', 19.9444, 54.7256, 'RU'],
  ['Baltique', 19.0, 55.0, null], ['GolfeFinlande', 25.0, 60.0, null],
  ['Ladoga', 31.5, 61.0, null], ['Pskov', 28.33, 57.82, 'RU'],
  ['Narva(EE)', 28.19, 59.38, 'EE'], ['Cesis(LV)', 25.29, 57.31, 'LV']
];
for (const [n, x, y, att] of probes) {
  const got = any(x, y);
  console.log(' ', n, '→', got || 'BLANC', att && got !== att ? '  ATTENDU ' + att : '');
}
// carte des blancs (cellules couvertes par AUCUN bloc)
const x0 = 19.5, x1 = 31.5, l0 = 53.8, l1 = 60.8, nx = 96, ny = 56;
console.log('--- blancs (#) région baltique ---');
for (let j = ny - 1; j >= 0; j--) {
  const lat = l0 + (l1 - l0) * j / ny; let row = '';
  for (let i = 0; i < nx; i++) { const x = x0 + (x1 - x0) * i / nx; row += any(x, lat) ? '.' : '#'; }
  console.log(lat.toFixed(1) + ' ' + row);
}
