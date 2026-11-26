#!/usr/bin/env node
// v9co.js — SILHOUETTE TERRESTRE d'un pays :
//   node v9co.js <ISO> <n1levelsCSV>   → data/<ISO>/land9.json.gz (mode identifiants OSM)
// Principe : les relations frontalières des pays maritimes descendent en mer
// jusqu'aux eaux territoriales (segments maritime=yes) → côtes soudées et
// « simplifiées ». Ici on construit au contraire :
//   - frontières INTERNES (ways partagés par >= 2 régions) supprimées
//   - ways maritime=yes supprimés (arcs en pleine mer)
//   - ways natural=coastline AJOUTÉS : le vrai littoral OSM
//   - littoral étranger présent dans l'extrait écarté : un way y entre
//     seulement si son milieu est dans le polygone L2 du pays ET pas dans
//     celui d'un voisin (les L2 des voisins sont dans rels.json).
// Sortie : land9.json.gz { iso, nom, rings: [[ [wid,rev], ... ]] } où rings
// sont des CYCLES FERMÉS d'identifiants (chaque cycle annoté par usage) —
// et coastal.json.gz (ways littoral retenus, pour plonger dans v9flat).
'use strict';
const fs = require('fs'), zlib = require('zlib');
const [ISO, N1CSV] = process.argv.slice(2);
const WANT = new Set((N1CSV || '4').split(',').map(Number));
const D = '/home/user/artifacts/v9/data/' + ISO;
const rels = JSON.parse(zlib.gunzipSync(fs.readFileSync(D + '/rels.json.gz')).toString());
const ways = JSON.parse(zlib.gunzipSync(fs.readFileSync(D + '/ways.json.gz')).toString());
const nodes = JSON.parse(zlib.gunzipSync(fs.readFileSync(D + '/nodes.json.gz')).toString());
const wm = new Map(); for (const w of ways) wm.set(w.id, w);
const coordRep = new Map(); // coordonnees identiques -> noeud canonique
const nm = new Map();
for (let i = 0; i < nodes.ids.length; i++) nm.set(nodes.ids[i], [nodes.lons[i], nodes.lats[i]]);

const own = (r) => ((r.iso1 || '').toUpperCase() === ISO) || ((r.iso2 || '').toUpperCase().startsWith(ISO + '-'))
  || (ISO === 'GR' && /[\u0370-\u03FF]/.test(r.name || ''));
const l2s = rels.filter(r => r.level === 2);
const own2 = l2s.filter(r => r.iso1 === ISO);
let n1rels;
if (ISO === 'GR') n1rels = rels.filter(r => r.level === 6 && (r.name || '').includes('Ενότητα'));
else n1rels = rels.filter(r => WANT.has(r.level) && own(r) && r.iso1 !== undefined);
// usage parmi les régions SEULEMENT (le L2 national ne compte pas, sinon on
// perdrait les frontières internationales partagées pays+region)
const use = new Map();
for (const r of n1rels) for (const m of r.members) if (m.t === 1) use.set(m.id, (use.get(m.id) || 0) + 1);
let nInternes = 0;
for (const c of use.values()) if (c >= 2) nInternes++;

// ---- anneaux L2 (pour filtre d'appartenance du littoral) ----
function chainRings(rel) {
  const avail = rel.members.filter(m => m.t === 1 && (m.role === '' || m.role === 'outer')).map(m => m.id).filter(id => wm.has(id));
  const used = new Set(); const rings = [];
  const byEnd = new Map();
  for (const wid of avail) { const refs = wm.get(wid).refs;
    for (const e of [refs[0], refs[refs.length - 1]]) { if (!byEnd.has(e)) byEnd.set(e, []); byEnd.get(e).push(wid); } }
  for (const start of avail) {
    if (used.has(start)) continue; used.add(start);
    const r0 = wm.get(start).refs;
    const chain = [[start, 0]];
    let end = r0[r0.length - 1], st = r0[0];
    let g = 0;
    while (end !== st && g++ < 100000) {
      const c = (byEnd.get(end) || []).filter(w => !used.has(w));
      if (!c.length) break; const w = c[0]; used.add(w);
      const r = wm.get(w).refs;
      if (r[0] === end) { chain.push([w, 0]); end = r[r.length - 1]; }
      else { chain.push([w, 1]); end = r[0]; }
    }
    if (end === st) rings.push(chain);
  }
  return rings;
}
function ringCoords(chain) {
  const pts = [];
  for (const [wid, rev] of chain) {
    const refs = wm.get(wid).refs;
    const s = rev ? refs.slice().reverse() : refs;
    for (let i = 0; i + 1 < s.length; i++) { const c = nm.get(s[i]); if (c) pts.push(c); }
  }
  return pts;
}
const ownPaths = [];
let n1open = 0;
for (const r of n1rels) { const rs = chainRings(r); if (!rs.length) n1open++; for (const rg of rs) ownPaths.push(ringCoords(rg)); }
const foreignPaths = [];
for (const r of rels) {
  if (!WANT.has(r.level) || r.iso1 === undefined || r.iso1 === ISO) continue;
  if (r.iso1.length !== 2 || !/^[A-Z]{2}$/.test(r.iso1)) continue;
  if (own(r)) continue;
  for (const rg of chainRings(r)) foreignPaths.push(ringCoords(rg));
}

function pip(paths, x, y) {
  let inside = false;
  for (const po of paths) {
    for (let i = 0; i + 1 < po.length; i++) {
      const [x1, y1] = po[i], [x2, y2] = po[i + 1];
      if ((y1 > y) !== (y2 > y)) { const xi = (x2 - x1) * (y - y1) / (y2 - y1) + x1; if (x < xi) inside = !inside; }
    }
  }
  return inside;
}
// ---- sélection des ways du contour ----
// ---- index spatial du littoral (grille 0.01°) ----
const coastSegs = [];
const grid = new Map();
const CELL = 0.01;
function gkey(x, y) { return Math.floor(x / CELL) + ',' + Math.floor(y / CELL); }
for (const w of ways) {
  if (!(w.tags || {}).natural || w.tags.natural !== 'coastline') continue;
  const refs = w.refs;
  for (let i = 0; i + 1 < refs.length; i++) {
    const a = nm.get(refs[i]), b = nm.get(refs[i + 1]);
    if (!a || !b) continue;
    const idx = coastSegs.length; coastSegs.push([a[0], a[1], b[0], b[1]]);
    const k1 = gkey(a[0], a[1]), k2 = gkey(b[0], b[1]);
    if (!grid.has(k1)) grid.set(k1, []); grid.get(k1).push(idx);
    if (k1 !== k2) { if (!grid.has(k2)) grid.set(k2, []); grid.get(k2).push(idx); }
  }
}
function distCoast(x, y) {
  let best = 1e9;
  const gx = Math.floor(x / CELL), gy = Math.floor(y / CELL);
  const seen = new Set();
  for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) {
    const l = grid.get((gx + dx) + ',' + (gy + dy));
    if (!l) continue;
    for (const i of l) { if (seen.has(i)) continue; seen.add(i);
      const [x0, y0, x1, y1] = coastSegs[i];
      const ddx = x1 - x0, ddy = y1 - y0;
      const L = ddx * ddx + ddy * ddy;
      let t = L ? ((x - x0) * ddx + (y - y0) * ddy) / L : 0;
      t = Math.max(0, Math.min(1, t));
      const ex = x0 + t * ddx - x, ey = y0 + t * ddy - y;
      const d = ex * ex + ey * ey;
      if (d < best) best = d;
    }
  }
  return Math.sqrt(best);
}
const TOLC = 0.0018; // ~200 m : plus proche partout => « ligne de base » doublant le littoral
const kept = new Map();
let nMar = 0, nCoastAll = 0, nCoastOut = 0, nBase = 0, nMer = 0;
for (const w of ways) {
  const t = w.tags || {};
  if (t.natural === 'coastline') {
    nCoastAll++;
    const refs = w.refs; const mid = refs[Math.floor(refs.length / 2)];
    const c = nm.get(mid);
    if (!c) continue;
    if (ownPaths.length && !pip(ownPaths, c[0], c[1])) { nCoastOut++; continue; }
    if (foreignPaths.some(fp => pip(fp, c[0], c[1]))) { nCoastOut++; continue; }
    kept.set(w.id, 'coast'); continue;
  }
  if ((use.get(w.id) || 0) >= 2) continue;      // frontière interne de région
  if (t.maritime === 'yes') nMar++;
  else nBase++;
  kept.set(w.id, 'adm');
}
// ---- graphe & cycles (traversée planaire, cf v9n1.js) ----
const MY = (lat) => Math.asinh(Math.tan(lat * Math.PI / 180)) * 180 / Math.PI;
let he = [], xy = new Map(), byNode = new Map();
function buildGraph(rep) {
  he = []; xy = new Map(); byNode = new Map();
  const R = (x) => (rep && rep.has(x)) ? rep.get(x) : x;
  // fusion par coordonnées identiques (noeuds distincts au même point)
  const cRep = new Map();
  const C = (x) => {
    if (cRep.has(x)) return cRep.get(x);
    const p = nm.get(x); if (!p) { cRep.set(x, x); return x; }
    const key = Math.round(p[0] * 1e6) + '|' + Math.round(p[1] * 1e6);
    let v = coordRep.get(key);
    if (v === undefined) { coordRep.set(key, x); v = x; }
    cRep.set(x, v); return v;
  };
  // 1) segments unitaires (coordonnées lon/lat pour l'intersection)
  const PTS = new Map(); // node -> [lon,lat] (synthétiques inclus)
  function P(n) { if (PTS.has(n)) return PTS.get(n); const p = nm.get(n); if (p) PTS.set(n, p.slice()); return p; }
  const segs = [];
  for (const [wid] of kept) {
    const refs = wm.get(wid).refs;
    const ns = [];
    for (const r of refs) { const e = C(R(r)); if (!ns.length || ns[ns.length - 1] !== e) ns.push(e); }
    const coast = kept.get(wid) === 'coast' ? 1 : 0;
    for (let i = 0; i + 1 < ns.length; i++) segs.push({ a: ns[i], b: ns[i + 1], c: coast, o: 1 });
  }
  // 2) découpage aux vraies intersections (arcs admin côte/mer qui croisent)
  const CG = 0.02;
  const cg = new Map();
  for (let i = 0; i < segs.length; i++) {
    const A = P(segs[i].a), B = P(segs[i].b); if (!A || !B) continue;
    segs[i].A = A; segs[i].B = B;
    const x0 = Math.floor(Math.min(A[0], B[0]) / CG), x1 = Math.floor(Math.max(A[0], B[0]) / CG);
    const y0 = Math.floor(Math.min(A[1], B[1]) / CG), y1 = Math.floor(Math.max(A[1], B[1]) / CG);
    for (let x = x0; x <= x1; x++) for (let y = y0; y <= y1; y++) {
      const k = x + ',' + y; if (!cg.has(k)) cg.set(k, []); cg.get(k).push(i);
    }
  }
  let crossN = 0;
  const crossAt = new Map(); // segIdx -> [{t, node(seq)}]
  const tested = new Set();
  for (let i = 0; i < segs.length; i++) {
    const s1 = segs[i];
    if (!s1.A || s1.c) continue;                  // seuls les segments ADMIN traquent les croisements
    const x0 = Math.floor(Math.min(s1.A[0], s1.B[0]) / CG), x1 = Math.floor(Math.max(s1.A[0], s1.B[0]) / CG);
    const y0 = Math.floor(Math.min(s1.A[1], s1.B[1]) / CG), y1 = Math.floor(Math.max(s1.A[1], s1.B[1]) / CG);
    for (let x = x0; x <= x1; x++) for (let y = y0; y <= y1; y++) {
      const l = cg.get(x + ',' + y); if (!l) continue;
      for (const j of l) {
        const s2 = segs[j];
        if (j <= i || !s2.A) continue;
        if (s1.a === s2.a || s1.a === s2.b || s1.b === s2.a || s1.b === s2.b) continue;
        const pk = i + '|' + j;
        if (tested.has(pk)) continue; tested.add(pk);
        const r = cross(s1, s2);
        if (!r) continue;
        const node = 'x' + (crossN++);
        PTS.set(node, [r[2], r[3]]);
        if (!crossAt.has(i)) crossAt.set(i, []); crossAt.get(i).push({ t: r[0], node });
        if (!crossAt.has(j)) crossAt.set(j, []); crossAt.get(j).push({ t: r[1], node });
      }
    }
  }
  function cross(s1, s2) {
    const [ax, ay] = s1.A, [bx, by] = s1.B, [cx, cy] = s2.A, [dx, dy] = s2.B;
    const r1x = bx - ax, r1y = by - ay, r2x = dx - cx, r2y = dy - cy;
    const den = r1x * r2y - r1y * r2x;
    if (!den) return null;
    const ex = cx - ax, ey = cy - ay;
    const t1 = (ex * r2y - ey * r2x) / den;
    const t2 = (ex * r1y - ey * r1x) / den;
    if (t1 <= 1e-12 || t1 >= 1 - 1e-12 || t2 <= 1e-12 || t2 >= 1 - 1e-12) return null;
    return [t1, t2, ax + t1 * r1x, ay + t1 * r1y];
  }
  // 3) demi-arêtes sur les sous-segments
  function addHalf(a, b, c, o) { he.push({ a: b, t: undefined, u: false, c, o }); return he.length - 1; }
  const seenPair = new Set();
  for (let i = 0; i < segs.length; i++) {
    const s = segs[i];
    if (!s.A) continue;
    const cuts = (crossAt.get(i) || []).slice().sort((p, q) => p.t - q.t);
    const chain = [s.a]; for (const ct of cuts) chain.push(ct.node); chain.push(s.b);
    for (let m = 0; m + 1 < chain.length; m++) {
      const a = chain[m], b = chain[m + 1];
      if (a === b) continue;
      const kk = String(a) + '|' + String(b);
      if (seenPair.has(kk)) continue;
      seenPair.add(kk);
      const h1 = addHalf(a, b, s.c, s.o), h2 = addHalf(b, a, s.c, 0);
      he[h1].t = h2; he[h2].t = h1;
    }
  }
  for (const h of he) {
    if (!xy.has(h.a)) { const p = P(h.a); if (!p) { h.dead = true; continue; } xy.set(h.a, [p[0], MY(p[1])]); }
    const b = he[h.t].a;
    if (!xy.has(b)) { const p = P(b); if (!p) { h.dead = true; continue; } xy.set(b, [p[0], MY(p[1])]); }
    const ca = xy.get(h.a), cb = xy.get(b);
    h.ang = Math.atan2(cb[1] - ca[1], cb[0] - ca[0]);
  }
  for (let k = 0; k < he.length; k++) {
    if (he[k].dead) continue;
    let l = byNode.get(he[k].a); if (!l) byNode.set(he[k].a, l = []);
    l.push(k);
  }
  for (const l of byNode.values()) l.sort((i, j) => he[i].ang - he[j].ang);
}
const DBG = 1;
const fsx = require('fs'); const dbgF = fsx.createWriteStream('/tmp/hrdbg.log');
buildGraph(null);
// ---- snap des extrémités pendantes : bouches de rivière/jonctions frontière-côte ----
const rep = new Map();
{
  const dang = [];
  const admPos = new Map();
  const GRID = 0.02;
  for (const [v, l] of byNode) {
    if (l.length === 1) { const p = nm.get(v); if (p) dang.push({ v, x: p[0], y: p[1], done: false }); }
    else {
      let hasAdm = false;
      for (const k of l) { if (!he[k].c) { hasAdm = true; break; } }
      if (hasAdm) { const p = nm.get(v); if (p) admPos.set(v, p); }
    }
  }
  function gridize(getter, items) {
    const g = new Map();
    for (const it of items) { const p = getter(it); const k = Math.floor(p[0] / GRID) + ',' + Math.floor(p[1] / GRID);
      if (!g.has(k)) g.set(k, []); g.get(k).push(it); }
    return g;
  }
  const dgr = gridize(v => admPos.get(v), [...admPos.keys()]);   // noeuds admin
  const dgr2 = gridize(d => [d.x, d.y], dang);                   // dangles
  function closest(gr, x, y, lim, skip) {
    const gx = Math.floor(x / GRID), gy = Math.floor(y / GRID), r = Math.ceil(lim / GRID);
    let best = null, bd = lim * lim;
    for (let dx = -r; dx <= r; dx++) for (let dy = -r; dy <= r; dy++) {
      const l = gr.get((gx + dx) + ',' + (gy + dy)); if (!l) continue;
      for (const it of l) {
        if (it.done) continue;
        if (skip && skip(it)) continue;
        const p = it.x !== undefined ? [it.x, it.y] : admPos.get(it);
        const d = (p[0] - x) ** 2 + ((p[1] - y) * 0.74) ** 2;
        if (d < bd) { bd = d; best = it; }
      }
    }
    return best;
  }
  const RAD_A = 0.004, RAD_D = 0.02;
  let nA = 0, nP = 0;
  for (const d of dang) {
    if (d.done) continue;
    const a = closest(dgr, d.x, d.y, RAD_A);
    if (a) { rep.set(d.v, a); d.done = true; nA++; continue; }
    const o = closest(dgr2, d.x, d.y, RAD_D, it => it === d);
    if (o) { rep.set(d.v, o.v); o.done = true; d.done = true; nP++; }
  }
  if (DBG) dbgF.write('SNAP adm=' + nA + ' pair=' + nP + ' dangles=' + dang.length + '\n');
}
if (rep.size) buildGraph(rep);
function prevInRot(v, k) { const l = byNode.get(v); return l[(l.indexOf(k) - 1 + l.length) % l.length]; }
function logCyc(tag, cyc, n, ccw, nc, wv) { let x0=1e9,y0=-1e9,x1=-1e9,y1=1e9 
  for (let i = 0; i < n; i++) { const p = xy.get(cyc.path[i]); if (!p) continue; if (p[0]<x0) x0=p[0]; if (p[0]>x1) x1=p[0]; if (p[1]>y0) y0=p[1]; if (p[1]<y1) y1=p[1]; } 
  dbgF.write(tag + ' pts=' + n + ' ccw=' + ccw + ' nco=' + nc + ' wv=' + wv + ' lon[' + x0.toFixed(2) + ',' + x1.toFixed(2) + '] lat[' + (Math.atan(Math.sinh(y1*Math.PI/180))*180/Math.PI).toFixed(2) + ',' + (Math.atan(Math.sinh(y0*Math.PI/180))*180/Math.PI).toFixed(2) + ']\n'); }
const cycles = [];
let nBroken = 0; const brk = { dead: 0, used: 0, cap: 0 };
for (let k0 = 0; k0 < he.length; k0++) {
  if (he[k0].dead || he[k0].u) continue;
  const path = []; const eds = []; let k = k0; let broken = false;
  for (let g = 0; ; g++) {
    if (g > 400000 || he[k].dead || he[k].u) { broken = true; brk[he[k].dead ? 'dead' : he[k].u ? 'used' : 'cap']++; break; }
    he[k].u = true; he[he[k].t].u = true;
    path.push(he[k].a); eds.push({ o: he[k].o, c: he[k].c });
    const t = he[k].t; k = prevInRot(he[t].a, t);
    if (k === k0) break;
  }
  if (broken) nBroken++;
  if (path.length > 2) cycles.push({ path, eds, broken });
}
// ---- classement des faces : convention OSM, TERRE À GAUCHE des coastline ----
// une face est MER si la majorité de ses côtés coastline la placent côté eau
const INV = (y) => Math.atan(Math.sinh(y * Math.PI / 180)) * 180 / Math.PI;
if (DBG) { dbgF.write('BROKEN=' + nBroken + ' ' + JSON.stringify(brk) + '\n');
  for (const cyc of cycles) if (cyc.broken && cyc.path.length > 1500) { let x0=1e9,x1=-1e9,y0=1e9,y1=-1e9;
    for (const id of cyc.path) { const p = xy.get(id); if (!p) continue; x0=Math.min(x0,p[0]);x1=Math.max(x1,p[0]);y0=Math.min(y0,p[1]);y1=Math.max(y1,p[1]); }
    dbgF.write('FACE CASSEE pts=' + cyc.path.length + ' lon[' + x0.toFixed(2) + ',' + x1.toFixed(2) + '] lat[' + INV(y0).toFixed(2) + ',' + INV(y1).toFixed(2) + ']\n'); } }
let nSea = 0, nGhost = 0;
const finalCycles = [];
for (const cyc of cycles) {
  const n = cyc.path.length;
  let A = 0;
  for (let i = 0; i < n; i++) {
    const p = xy.get(cyc.path[i]), q = xy.get(cyc.path[(i + 1) % n]);
    if (p && q) A += p[0] * q[1] - q[0] * p[1];
  }
  const ccw = A > 0;
  let nc = 0, wv = 0;
  for (const e of cyc.eds) if (e.c) { nc++; if ((e.o === 1) === ccw) wv++; }
  if (nc > 0 && wv * 2 > nc) { nSea++;
    if (DBG && cyc.path.length > 3000) logCyc('MER', cyc, n, ccw, nc, wv);
    continue; }
  if (DBG && cyc.path.length > 3000) logCyc('TERRE', cyc, n, ccw, nc, wv);
  // point d'échantillon : côté intérieur de l'arête la plus courte
  let bi = 0, bd = 1e18, bx1 = 0, by1 = 0, bx2 = 0, by2 = 0;
  for (let i = 0; i < n; i++) {
    const p = xy.get(cyc.path[i]), q = xy.get(cyc.path[(i + 1) % n]);
    if (!p || !q) continue;
    const d = (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2;
    if (d < bd) { bd = d; bi = i; bx1 = p[0]; by1 = p[1]; bx2 = q[0]; by2 = q[1]; }
  }
  const mx = (bx1 + bx2) / 2, my = (by1 + by2) / 2;
  const dx = bx2 - bx1, dy = by2 - by1, L = Math.hypot(dx, dy) || 1;
  const eps = 5e-5;
  const nx = mx + (ccw ? -dy : dy) * eps / L, ny = my + (ccw ? dx : -dx) * eps / L;
  if (ownPaths.length && !pip(ownPaths, nx, INV(ny))) { nGhost++;
    if (DBG && cyc.path.length > 500) dbgF.write('HORS L2 ccw=' + ccw + ' nco=' + nc + ' wv=' + wv + ' echant lon=' + nx.toFixed(3) + ' lat=' + INV(ny).toFixed(3) + '\n');
    continue; } // hors L2 : étranger
  finalCycles.push(cyc);
  if (DBG && cyc.path.length > 500) dbgF.write('GARDE ccw=' + ccw + ' nco=' + nc + ' wv=' + wv + ' echant lon=' + nx.toFixed(3) + ' lat=' + INV(ny).toFixed(3) + '\n');
}
if (DBG) {
  const info = [];
  for (const cyc of cycles) { const n = cyc.path.length; let x0=1e9,x1=-1e9,y0=1e9,y1=-1e9;
    for (const id of cyc.path) { const p = xy.get(id); if (!p) continue; x0=Math.min(x0,p[0]);x1=Math.max(x1,p[0]);y0=Math.min(y0,p[1]);y1=Math.max(y1,p[1]); }
    info.push({ n, x0, x1, y0: INV(y0), y1: INV(y1) }); }
  fsx.writeFileSync('/tmp/HRcycles.json', JSON.stringify(info));
}
// ---- sortie land9 (identifiants OSM, façon v9ring) ----
// on remonte chaque cycle en liste de ways: index des ways par extrémite...
// reconstruction: pour un cycle de nodes, retrouver les ways... simplification:
// on stocke directement les COORDONNÉES (v9co = étape finale, pas d'augmentation future)
const ps = [];
let pts = 0, x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
for (const c of finalCycles) {
  let d = ''; let n = 0;
  for (const id of c.path) {
    const q = xy.get(id); if (!q) continue;
    d += (n === 0 ? 'M' : 'L') + +q[0].toFixed(5) + ' ' + +q[1].toFixed(5);
    n++;
  }
  if (n > 2) { d += 'Z'; ps.push(d); pts += n; }
  for (const id of c.path) { const q = xy.get(id); if (!q) continue;
    if (q[0] < x0) x0 = q[0]; if (q[0] > x1) x1 = q[0]; if (q[1] < y0) y0 = q[1]; if (q[1] > y1) y1 = q[1]; }
}
const blk = { iso: ISO, nom: (own2[0] && own2[0].name) || ISO, ps, b: [x0, y0, x1, y1],
  boucles: ps.length, internes: nInternes, maritime: nMar,
  littoral: nCoastAll - nCoastOut, littoralEcarte: nCoastOut, fantomes: nGhost, pts };
fs.writeFileSync(D + '/co9.json.gz', zlib.gzipSync(Buffer.from(JSON.stringify(blk)), { level: 9 }));
console.log(ISO, 'co: boucles=' + ps.length, 'pts=' + pts, 'littoral=' + (nCoastAll - nCoastOut),
  'ecarte=' + nCoastOut, 'maritime=' + nMar, 'internes=' + nInternes, 'fantomes=' + nGhost,
  (JSON.stringify(ps).length / 1e6).toFixed(1) + ' Mo');