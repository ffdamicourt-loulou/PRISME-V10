#!/usr/bin/env node
// v9n1.js — DISSOUT les régions : tracé NIVEAU PAYS SEUL (n1)
//   node v9n1.js <ISO>   → /home/user/artifacts/v9/out/n1/<ISO>.json.gz
// 1) ways utilisés par >= 2 anneaux du pays = frontières INTERNES → supprimés.
// 2) arêtes restantes = côtes + frontières internationales.
// 3) traversée PLANAIRE (rotation angulaire des demi-arêtes) : à un nœud
//    « pincé » (deux boucles du contour se touchent en un même nœud, ex.
//    Jungholz), l'appariement angulaire sépare correctement les boucles,
//    là où un chaînage glouton produirait des polygones qui se chevauchent.
'use strict';
const fs = require('fs'), zlib = require('zlib');
const ISO = process.argv[2];
const MODE = process.argv[3] || 'n1'; // n1 | n1d (dedup géométrique 10 m) | l2
const D = '/home/user/artifacts/v9/data/' + ISO;
let L;
if (MODE === 'l2') {
  // TRACÉ PAYS SEUL : anneaux de la relation L2 (frontière internationale
  // telle qu'OSM la trace). Aucune ligne interne possible par construction.
  const rels = JSON.parse(zlib.gunzipSync(fs.readFileSync(D + '/rels.json.gz')).toString());
  const ways = JSON.parse(zlib.gunzipSync(fs.readFileSync(D + '/ways.json.gz')).toString());
  const WM = new Map(); for (const w of ways) WM.set(w.id, w.refs);
  const own = (r) => ((r.iso2 || '').toUpperCase().startsWith(ISO + '-')) || ((r.iso1 || '').toUpperCase() === ISO)
    || (ISO === 'GR' && /[\u0370-\u03FF]/.test(r.name || ''));
  const own2 = rels.filter(r => r.level === 2 && own(r) && !/_INSEE|constituent/i.test(r.name || ''));
  // MT : la relation L2 n'est qu'un conteneur → anneaux via toutes les L2 du pays
  // priorite a l'appariement EXACT iso1=ISO (evite RS-KM Kosovo -> Serbie)
  let sel = rels.filter(r => r.level === 2 && (r.iso1 || '').toUpperCase() === ISO && !/_INSEE|constituent/i.test(r.name || ''));
  if (!sel.length) sel = own2.length ? own2 : rels.filter(r => r.level === 2 && own(r));
  function ringsForRelation(rel) {
    const outers = rel.members.filter(m => m.t === 1 && (m.role === '' || m.role === 'outer')).map(m => m.id);
    const avail = outers.filter(id => WM.has(id));
    const used = new Set(); const rings = [];
    const byEnd = new Map();
    for (const wid of avail) { const refs = WM.get(wid);
      for (const e of [refs[0], refs[refs.length - 1]]) { if (!byEnd.has(e)) byEnd.set(e, []); byEnd.get(e).push(wid); } }
    for (const startWid of avail) {
      if (used.has(startWid)) continue; used.add(startWid);
      const refs0 = WM.get(startWid);
      const chain = [[startWid, 0]];
      let curEnd = refs0[refs0.length - 1]; let curStart = refs0[0];
      let guard = 0;
      while (curEnd !== chain[0] && guard++ < 200000) {
        const cands = (byEnd.get(curEnd) || []).filter(w => !used.has(w));
        if (!cands.length) break; const wid = cands[0]; used.add(wid);
        const refs = WM.get(wid);
        if (refs[0] === curEnd) { chain.push([wid, 0]); curEnd = refs[refs.length - 1]; }
        else if (refs[refs.length - 1] === curEnd) { chain.push([wid, 1]); curEnd = refs[0]; }
        else break;
      }
      guard = 0;
      while (curStart !== curEnd && guard++ < 200000) {
        const cands = (byEnd.get(curStart) || []).filter(w => !used.has(w));
        if (!cands.length) break; const wid = cands[0]; used.add(wid);
        const refs = WM.get(wid);
        if (refs[refs.length - 1] === curStart) { chain.unshift([wid, 0]); curStart = refs[0]; }
        else if (refs[0] === curStart) { chain.unshift([wid, 1]); curStart = refs[refs.length - 1]; }
        else break;
      }
      if (curStart === curEnd && chain.length) rings.push(chain);
    }
    return rings;
  }
  let rings = []; let nom = ISO;
  for (const r of sel) { nom = r.name || nom; for (const rg of ringsForRelation(r)) rings.push(rg); }
  L = { iso: ISO, nom, n: rings.length, rings };
  if (!rings.length) { console.error(ISO, 'L2: AUCUN anneau !'); process.exit(1); }
} else {
  L = JSON.parse(zlib.gunzipSync(fs.readFileSync(D + '/land9.json.gz')).toString());
}
const W = JSON.parse(zlib.gunzipSync(fs.readFileSync(D + '/ways.json.gz')).toString());
const N = JSON.parse(zlib.gunzipSync(fs.readFileSync(D + '/nodes.json.gz')).toString());
const wm = new Map(W.map(w => [w.id, w.refs]));
const nm = new Map();
for (let i = 0; i < N.ids.length; i++) nm.set(N.ids[i], [N.lons[i], N.lats[i]]);

const MY = (lat) => Math.asinh(Math.tan(lat * Math.PI / 180)) * 180 / Math.PI;

// 1) usage de chaque way sur tous les anneaux du pays
const use = new Map();
for (const ring of L.rings) for (const [wid] of ring) use.set(wid, (use.get(wid) || 0) + 1);
let nInternes = 0;
for (const c of use.values()) if (c >= 2) nInternes++;

// 2) demi-arêtes (heuristiques externes uniquement)
// he[k] = { a: nodeFrom, b: nodeTo, ang: angle a→b, u }
const he = [];
function addHalf(a, b) { he.push({ a: b, ang: NaN, u: false }); return he.length - 1; }
// MODE n1d en plus : les frontières régionales parfois DOUBLÉES dans OSM par
// des ways DISTINCTS quasi confondus (node ids différents, écart ~ mètres)
// ne sont jamais comptées usage>=2. Dedup géométrique : toute arête dont le
// milieu (arrondi à 1e-4 ≈ 10 m) apparaît >= 2 fois est une frontière
// interne dupliquée → on supprime TOUTES ses copies.
const GD = (process.argv[4] === 'gd') ? new Map() : null;
function gdKey(a, b) {
  const ca = nm.get(a), cb = nm.get(b); if (!ca || !cb) return null;
  const mx = (ca[0] + cb[0]) / 2, my = (MY(ca[1]) + MY(cb[1])) / 2;
  return Math.round(mx * 1e4) + ',' + Math.round(my * 1e4);
}
if (GD) {
  for (const ring of L.rings) for (const [wid, rev] of ring) {
    if ((use.get(wid) || 1) >= 2) continue;
    const refs = wm.get(wid); if (!refs || refs.length < 2) continue;
    const sr = rev ? refs.slice().reverse() : refs;
    for (let i = 0; i + 1 < sr.length; i++) {
      const k = gdKey(sr[i], sr[i + 1]); if (k) GD.set(k, (GD.get(k) || 0) + 1);
    }
  }
}
let gdLines = 0, gdNodes = 0;
for (const ring of L.rings) for (const [wid, rev] of ring) {
  if ((use.get(wid) || 1) >= 2) continue;
  const refs = wm.get(wid); if (!refs || refs.length < 2) continue;
  for (let i = 0; i + 1 < refs.length; i++) {
    const a = refs[i], b = refs[i + 1];
    if (a === b) continue;
    if (GD) {
      const k = gdKey(a, b);
      if (k && GD.get(k) >= 2) { gdLines++; continue; }
    }
    const h1 = addHalf(a, b), h2 = addHalf(b, a);
    he[h1].t = h2; he[h2].t = h1;
  }
}
if (GD) console.error(ISO + ' gd: ' + gdLines + ' arêtes dupliquées supprimées');
// angles (mercator) + rotation triée par nœud
const xy = new Map(); // node -> [x,y]
for (const h of he) {
  let c = xy.get(h.a);
  if (!c) { const p = nm.get(h.a); if (!p) { h.dead = true; continue; } c = [p[0], MY(p[1])]; xy.set(h.a, c); }
  const d = xy.get(h.t !== undefined ? he[h.t].a : h.a);
  // cible:
  let tgt = h.a; if (h.t !== undefined) tgt = he[h.t].a;
  const c2 = nm.get(tgt);
  if (!c2) { h.dead = true; continue; }
  const c2m = [c2[0], MY(c2[1])];
  xy.set(tgt, c2m);
  h.ang = Math.atan2(c2m[1] - c[1], c2m[0] - c[0]);
}
const byNode = new Map(); // node -> [indices he sorted by angle]
for (let k = 0; k < he.length; k++) {
  if (he[k].dead) continue;
  let l = byNode.get(he[k].a); if (!l) byNode.set(he[k].a, l = []);
  l.push(k);
}
for (const l of byNode.values()) l.sort((i, j) => he[i].ang - he[j].ang);
function prevInRot(v, k) {
  const l = byNode.get(v); const i = l.indexOf(k);
  return l[(i - 1 + l.length) % l.length];
}
// 3) traversée : chaque cycle de contour exactement une fois
const cycles = [];
for (let k0 = 0; k0 < he.length; k0++) {
  if (he[k0].dead || he[k0].u) continue;
  const path = [];
  let k = k0;
  for (let guard = 0; ; guard++) {
    if (guard > 400000) { console.error(ISO, 'guard!'); break; }
    if (he[k].dead || he[k].u) break;
    he[k].u = true; he[he[k].t].u = true;
    path.push(he[k].a);
    // next : demi-arête suivante dans la face = twin puis rotation précédente
    const t = he[k].t;
    const v = he[t].a;
    k = prevInRot(v, t);
    if (k === k0) break;
  }
  if (path.length > 2) cycles.push(path);
}

// 4) élimination des cycles-fantômes : les frontières régionales dupliquées
//    dans OSM (un jeu de ways par relation régionale) survivent au filtre
//    usage>=2 et forment des cycles ENTIÈREMENT CONTENUS dans un autre cycle
//    du pays (ex. le land de Vienne dans l'Autriche). Un tel cycle annule la
//    zone au rendu (parité evenodd) et fait apparaître la région tracée.
//    Règle : on garde les cycles de profondeur d'imbrication PAIRE.
// NB: un vrai trou (enclave d'un autre pays dans le nôtre) serait aussi de
//    profondeur impaire, mais le périmètre retenu n'a pas d'enclave interne.
const coordCyc = cycles.map(cyc => cyc.map(id => xy.get(id)).filter(Boolean));
function contains(polyArrays, p) {
  // p à l'intérieur (impair de franchissements) d'un des polygones ?
  const [px, py] = p;
  let inside = false;
  for (const pa of polyArrays) {
    // bbox rapide
    let hit = false;
    for (let i = 0; i + 1 < pa.length; i++) {
      const x1 = pa[i][0], y1 = pa[i][1], x2 = pa[i + 1][0], y2 = pa[i + 1][1];
      if ((y1 > py) !== (y2 > py)) {
        const xi = (x2 - x1) * (py - y1) / (y2 - y1) + x1;
        if (px < xi) hit = !hit;
      }
    }
    if (hit) inside = !inside ? true : false; // cumul de parité
  }
  return inside;
}
const depth = coordCyc.map((pa, i) => {
  const p = pa[0]; let d = 0;
  const others = coordCyc.map((pb, j) => (j !== i ? pb : null)).filter(Boolean);
  if (contains(others, p)) d++;
  return d;
});
const kept = cycles.filter((cyc, i) => depth[i] % 2 === 0);
if (kept.length !== cycles.length) console.error(ISO, 'cycles fantômes supprimés:', cycles.length - kept.length);
const finalCycles = kept;

function toPath(nodes, close) {
  let d = '', n = 0;
  for (const id of nodes) {
    const c = xy.get(id); if (!c) continue;
    d += (n === 0 ? 'M' : 'L') + +c[0].toFixed(5) + ' ' + +c[1].toFixed(5);
    n++;
  }
  if (close && n > 2) d += 'Z';
  return n > 2 ? d : '';
}

const ps = []; let pts = 0;
let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
const seen = new Set();
for (const cyc of finalCycles) {
  const d = toPath(cyc, true);
  if (!d) continue;
  ps.push(d); pts += cyc.length;
  for (const id of cyc) seen.add(id);
}
for (const id of seen) {
  const c = xy.get(id); if (!c) continue;
  const [x, y] = c;
  if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
}

const blk = {
  iso: ISO, nom: L.nom || ISO,
  ps, b: [x0, y0, x1, y1],
  boucles: ps.length, ouvertes: 0,
  internes: nInternes, pts
};
fs.mkdirSync('/home/user/artifacts/v9/out/n1', { recursive: true });
fs.writeFileSync('/home/user/artifacts/v9/out/n1/' + ISO + (MODE==='l2'?'.L2':(MODE==='n1d'?'.GD':'')) + '.json.gz',
  zlib.gzipSync(Buffer.from(JSON.stringify(blk)), { level: 9 }));
console.log(ISO, MODE, (L.nom || '').slice(0, 16),
  'boucles=' + ps.length, 'internes=' + nInternes,
  'pts=' + pts, (JSON.stringify(ps).length / 1e6).toFixed(1) + ' Mo');