#!/usr/bin/env node
// v9kgd.js — Kaliningrad : anneau exact cousu
//   A = frontière PL→RU exacte (bloc PL, mêmes ways OSM)
//   B = frontière LT→RU exacte (bloc LT)
//   C = côtes (hyperknot medium, grossier mais topologiquement correct)
// Écrit data/RU-hk/RU-KGD.geojson (remplace le fichier high corrompu).
'use strict';
const fs = require('fs'), zlib = require('zlib');
const V9 = '/home/user/artifacts/v9';
const ylat = (y) => Math.atan(Math.sinh(y * Math.PI / 180)) * 180 / Math.PI;
const myd = (lat) => Math.asinh(Math.tan(lat * Math.PI / 180)) * 180 / Math.PI;

function blockRings(file) {
  const b = JSON.parse(zlib.gunzipSync(fs.readFileSync(file)).toString());
  return b.ps.map(d => {
    const nums = d.replace(/M/g, ' ').trim().split(/L| /).filter(s => s.length).map(Number);
    // d = "Mx yLx yL..." → split on L, first token has M
    const toks = d.slice(1).split('L').map(s => s.split(' ').map(Number));
    return toks.map(([x, y]) => [x, ylat(y)]);
  });
}
// parse robust: ps = "Mlon yLlon y..."
function parsePs(d) {
  const toks = d.slice(1).split('L').map(s => s.split(' ').map(Number));
  return toks.map(([x, y]) => [x, ylat(y)]);
}

const plLoops = blockRings(V9 + '/out/final/PL.json.gz');
const ltLoops = blockRings(V9 + '/out/final/LT.json.gz');
console.log('PL boucles:', plLoops.length, 'LT boucles:', ltLoops.length);

const near = (ring, t) => { let bi = 0, bd = 1e9; for (let i = 0; i < ring.length; i++) { const d = (ring[i][0] - t[0]) ** 2 + (ring[i][1] - t[1]) ** 2; if (d < bd) { bd = d; bi = i; } } return bi; };
const d2 = (p, t) => (p[0] - t[0]) ** 2 + (p[1] - t[1]) ** 2;
function subPath(ring, i0, i1, dir) { // dir=+1 forward
  const out = [];
  let i = i0, guard = 0;
  while (guard++ <= ring.length) {
    out.push(ring[i]);
    if (i === i1) break;
    i = (i + dir + ring.length) % ring.length;
  }
  return out;
}
function passesNear(path, t, r) { return path.some(p => d2(p, t) < r * r); }

// --- A : PL, côte (J) → tri-point (T) -----------------------------------
const J = [19.65, 54.45], T = [22.79, 54.36];
let A = null;
for (const ring of plLoops) {
  if (Math.min(...ring.map(p => p[1])) > 54.8 || !passesNear(ring, T, 0.3)) continue;
  const iJ = near(ring, J), iT = near(ring, T);
  const fwd = subPath(ring, iJ, iT, +1), bwd = subPath(ring, iJ, iT, -1);
  const cand = [fwd, bwd].filter(p => passesNear(p, [21.0, 54.4], 0.25));
  if (cand.length) { A = cand[0]; console.log('A trouvé: PL ring', plLoops.indexOf(ring), 'pts:', A.length, 'de', A[0], 'à', A[A.length - 1]); break; }
}
if (!A) throw new Error('A introuvable');

// --- B : LT, tri-point (T) → P2 (pointe de la presqu'île Couronne) ------
const TIP = [20.996, 55.264];
let B = null;
for (const ring of ltLoops) {
  if (!passesNear(ring, T, 0.3)) continue;
  const iT = near(ring, T), iP = near(ring, TIP);
  const fwd = subPath(ring, iT, iP, +1), bwd = subPath(ring, iT, iP, -1);
  const cand = [fwd, bwd].filter(p => passesNear(p, [22.55, 55.08], 0.25));
  if (cand.length) { B = cand[0]; console.log('B trouvé: LT ring', ltLoops.indexOf(ring), 'pts:', B.length, 'de', B[0], 'à', B[B.length - 1]); break; }
}
if (!B) throw new Error('B introuvable');

// --- C : côtes medium, de la pointe → (19.804,54.442) -------------------
const med = JSON.parse(fs.readFileSync(V9 + '/data/RU-hk/RU-KGD-medium.geojson', 'utf8'));
const mring = med.geometry.coordinates[1][0];
const iTip = near(mring, TIP), iK = near(mring, [19.804, 54.442]);
const C = mring.slice(Math.min(iTip, iK), Math.max(iTip, iK) + 1);
if (iTip > iK) C.reverse(); // tip en premier
console.log('C trouvé: pts:', C.length, 'de', C[0], 'à', C[C.length - 1]);

// A doit démarrer au vertex coïncidant avec la fin de C (sinon la fermeture croise A)
const iA2 = near(A, C[C.length - 1]);
if (iA2 > 0 && iA2 < A.length - 1) { console.log('A rogné:', iA2, 'pts initiaux retirés (chevauchent la fin de C)'); A = A.slice(iA2); }

// --- assemblage ----------------------------------------------------------
const ring = [];
const push = (pts) => { for (const p of pts) { const l = ring[ring.length - 1]; if (!l || l[0] !== p[0] || l[1] !== p[1]) ring.push(p); } };
push(A); push(B); push(C); push([A[0]]); // fermeture
console.log('anneau KGD cousu:', ring.length, 'pts');

// --- validation ----------------------------------------------------------
function winding(x, y) { let w = 0; for (let i = 0; i < ring.length - 1; i++) { const a = ring[i], b = ring[i + 1];
  if (a[1] <= y) { if (b[1] > y && (b[0] - a[0]) * (y - a[1]) - (x - a[0]) * (b[1] - a[1]) > 0) w++; }
  else if (b[1] <= y && (b[0] - a[0]) * (y - a[1]) - (x - a[0]) * (b[1] - a[1]) < 0) w--; }
  return w; }
const probes = [['Kaliningrad', 20.511, 54.71], ['Zelenogradsk', 21.0117, 54.9578], ['Pionersky', 19.95, 54.96], ['Yantarny', 19.9444, 54.7256], ['Baltiysk', 19.91, 54.65], ['Nesterov', 22.8713, 54.38], ['Sovetsk', 22.6, 55.08], ['Chernyakhovsk', 21.81, 54.63], ['Gusev', 22.2, 54.59], ['Bagrationovsk', 20.64, 54.38], ['Morskoe(spit)', 20.55, 54.96], ['Rybachy(lagon)', 20.3, 54.6], ['Ozersk', 21.6, 54.83]];
for (const [n, x, y] of probes) console.log('  ', n, winding(x, y) !== 0 ? 'OK' : 'BLANC');
// aire
let As = 0; for (let i = 0; i < ring.length - 1; i++) { const a = ring[i], b = ring[i + 1]; As += a[0] * b[1] - b[0] * a[1]; }
const km2 = Math.abs(As / 2) * Math.pow(111.32 * Math.cos(54.7 * Math.PI / 180), 2);
console.log('aire km² ~', km2.toFixed(0), '(attendu ~13 400 dont lagon)');
// auto-intersections (hors out-and-back collé)
let nx = 0;
for (let i = 0; i < ring.length - 2; i++) for (let j = i + 2; j < ring.length - 1; j++) {
  const a = ring[i], b = ring[i + 1], c = ring[j], d2v = ring[j + 1];
  const den = (b[0] - a[0]) * (d2v[1] - c[1]) - (b[1] - a[1]) * (d2v[0] - c[0]);
  if (!den) continue;
  const t = ((c[0] - a[0]) * (d2v[1] - c[1]) - (c[1] - a[1]) * (d2v[0] - c[0])) / den;
  const u = ((c[0] - a[0]) * (b[1] - a[1]) - (c[1] - a[1]) * (b[0] - a[0])) / den;
  if (t > 0 && t < 1 && u > 0 && u < 1) nx++;
}
console.log('paires de segments sécants:', nx);

// --- écriture ------------------------------------------------------------
const backup = V9 + '/data/RU-hk/RU-KGD-hk-high-original.geojson';
if (!fs.existsSync(backup)) fs.copyFileSync(V9 + '/data/RU-hk/RU-KGD.geojson', backup);
const gj = { type: 'Feature', geometry: { type: 'MultiPolygon', coordinates: [[ring]] }, properties: { name: 'Kaliningrad', iso2: 'RU-KGD', note: 'stitched: PL/LT exact (blocs) + hyperknot medium coasts' } };
fs.writeFileSync(V9 + '/data/RU-hk/RU-KGD.geojson', JSON.stringify(gj));
console.log('data/RU-hk/RU-KGD.geojson réécrit (', ring.length, 'pts ). Original sauvé en RU-KGD-hk-high-original.geojson');
