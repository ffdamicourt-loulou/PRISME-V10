#!/usr/bin/env node
// v9flat.js — rend chaque pays déjà extrait en bloc JSON {nom, d} (Mercator, CF=1)
//   node v9flat.js <ISO>        → /home/user/artifacts/v9/out/blocks/<ISO>.json.gz
// d = un path SVG PAR ANNEAU (M…Z par anneau, leçon v8), coordonnées Mercator 5 déc.
'use strict';
const fs = require('fs'), zlib = require('zlib');
const ISO = process.argv[2];
const D = '/home/user/artifacts/v9/data/' + ISO;
const L = JSON.parse(zlib.gunzipSync(fs.readFileSync(D + '/land9.json.gz')).toString());
const W = JSON.parse(zlib.gunzipSync(fs.readFileSync(D + '/ways.json.gz')).toString());
const N = JSON.parse(zlib.gunzipSync(fs.readFileSync(D + '/nodes.json.gz')).toString());
const wm = new Map(W.map(w => [w.id, w.refs]));
const nm = new Map();
for (let i = 0; i < N.ids.length; i++) nm.set(N.ids[i], [N.lons[i], N.lats[i]]);
let nmiss = 0;
const MY = (lat) => Math.asinh(Math.tan(lat * Math.PI / 180)) * 180 / Math.PI;
let ringDs = [];
let pts = 0;
let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
// usage de chaque way sur l'ensemble des anneaux du pays : >=2 => frontière INTERNE
const use = new Map();
for (const ring of L.rings) for (const [wid] of ring) use.set(wid, (use.get(wid) || 0) + 1);
let nInternes = 0;
let ext = '';
function emit(extRun) {
  // extRun = liste de séquences de node ids contigus
  let started = false; let dRun = '';
  for (const seqs of extRun) {
    for (let i = 0; i < seqs.length; i++) {
      const c = nm.get(seqs[i]); if (!c) { nmiss++; continue; }
      const x = +c[0].toFixed(5), y = +MY(c[1]).toFixed(5);
      if (!started) { dRun += 'M' + x + ' ' + y; started = true; } else dRun += 'L' + x + ' ' + y;
    }
  }
  return dRun;
}
for (const ring of L.rings) {
  let ringD = '';
  let started = false;
  let run = [];   // ways externes consécutifs pour le path "ext"
  let runSeqs = [];
  const flush = () => { if (runSeqs.length) { ext += emit(runSeqs); run = []; runSeqs = []; } };
  for (const [wid, rev] of ring) {
    const refs = wm.get(wid);
    if (!refs || !refs.length) continue;
    const seq = rev ? refs.slice().reverse() : refs;
    for (let i = 0; i < seq.length; i++) {
      const nid = seq[i];
      const c = nm.get(nid);
      if (!c) { nmiss++; continue; }
      const x = +c[0].toFixed(5), y = +MY(c[1]).toFixed(5);
      if (!started) { ringD += 'M' + x + ' ' + y; started = true; }
      else ringD += 'L' + x + ' ' + y;
      if (x < x0) x0 = x; if (x > x1) x1 = x;
      if (y < y0) y0 = y; if (y > y1) y1 = y;
      pts++;
    }
    if ((use.get(wid) || 1) === 1) { runSeqs.push(seq); } else { nInternes++; flush(); }
  }
  flush();
  if (started) ringDs.push(ringD + 'Z');
}

const nom = L.nom || ISO;
const blk = { iso: ISO, nom, rings: ringDs, ext, b: [x0, y0, x1, y1], anneaux: L.n, pts, nmiss, nInternes };
fs.mkdirSync('/home/user/artifacts/v9/out/blocks', { recursive: true });
fs.writeFileSync('/home/user/artifacts/v9/out/blocks/' + ISO + '.json.gz', zlib.gzipSync(Buffer.from(JSON.stringify(blk)), { level: 9 }));
console.log(ISO, nom.slice(0, 14), 'anneaux=' + L.n, 'pts=' + pts, (nmiss ? 'MANQUANTS=' + nmiss : ''), (JSON.stringify(ringDs).length / 1e6).toFixed(1) + ' Mo');