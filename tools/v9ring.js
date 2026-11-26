#!/usr/bin/env node
// v9ring.js — silhouette pays en IDENTIFIANTS OSM (pas de coordonnées !).
//   node v9ring.js <outdir-extract> <ISO> <n1levels CSV> [annexISO...]
// Construit, à partir de rels.json/ways.json (extract.js niveaux 2,4,6) :
//  - silhouette du pays = UNION (concaténation, evenodd) des anneaux des
//    relations du niveau n1 (ex. FR: 4). Anneaux = chaînes de ways OSM,
//    stockés (wayId, rev). Fallback: relation L2 (si n1 vide).
//  - stocke land9.json.gz : { iso, nom, rings: [[ [wid,rev], ... ]], }
// Les micro-États annexés (args 4+) : leurs relations L2 sont ajoutées
// telles quelles à la silhouette (remplissent leur enclave, evenodd).
'use strict';
const fs = require('fs'), zlib = require('zlib');
const [OUTDIR, ISO, N1CSV, ...ANNEX] = process.argv.slice(2);
const N1 = new Set(N1CSV.split(',').map(Number));
const rels = JSON.parse(fs.readFileSync(OUTDIR + '/rels.json', 'utf8'));
const ways = JSON.parse(fs.readFileSync(OUTDIR + '/ways.json', 'utf8'));
const W = new Map(); for (const w of ways) W.set(w.id, w.refs);
const waysUsed = new Set();

function ringOf(waysUsedIds) { /* renvoie [[wid,rev],...] ou null si non fermé */ }

// chaîne les ways d'une relation en anneaux fermés
function ringsForRelation(rel) {
  const outers = rel.members.filter(m => m.t === 1 && (m.role === '' || m.role === 'outer')).map(m => m.id);
  const avail = outers.filter(id => W.has(id));
  const used = new Set();
  const rings = [];
  const endAt = []; // en -> {wid, endIdx} pour l'assemblage
  const byEnd = new Map(); // nodeId -> [{wid}]
  for (const wid of avail) {
    const refs = W.get(wid);
    for (const e of [refs[0], refs[refs.length - 1]]) {
      if (!byEnd.has(e)) byEnd.set(e, []);
      byEnd.get(e).push(wid);
    }
  }
  for (const startWid of avail) {
    if (used.has(startWid)) continue;
    used.add(startWid);
    const refs0 = W.get(startWid);
    const chain = [[startWid, 0]];
    let curEnd = refs0[refs0.length - 1];
    let curStart = refs0[0];
    // étendre par la fin
    let guard = 0;
    while (curEnd !== chainStartNode(chain, 0) && guard++ < 100000) {
      const cands = (byEnd.get(curEnd) || []).filter(w => !used.has(w));
      if (!cands.length) break;
      const wid = cands[0]; used.add(wid);
      const refs = W.get(wid);
      if (refs[0] === curEnd) { chain.push([wid, 0]); curEnd = refs[refs.length - 1]; }
      else if (refs[refs.length - 1] === curEnd) { chain.push([wid, 1]); curEnd = refs[0]; }
      else break;
    }
    // étendre par le début
    guard = 0;
    while (curStart !== curEnd && guard++ < 100000) {
      const cands = (byEnd.get(curStart) || []).filter(w => !used.has(w));
      if (!cands.length) break;
      const wid = cands[0]; used.add(wid);
      const refs = W.get(wid);
      if (refs[refs.length - 1] === curStart) { chain.unshift([wid, 0]); curStart = refs[0]; }
      else if (refs[0] === curStart) { chain.unshift([wid, 1]); curStart = refs[refs.length - 1]; }
      else break;
    }
    const closed = curStart === curEnd;
    if (closed) rings.push(chain);
    else process.stderr.write('  [rel ' + rel.id + '] anneau NON FERMÉ (' + chain.length + ' ways), ignoré\n');
  }
  return rings;
}
function chainStartNode(chain, _) {
  const [wid, rev] = chain[0];
  const refs = W.get(wid);
  return rev ? refs[refs.length - 1] : refs[0];
}

// sélections : uniquement les relations DU PAYS (préfixe iso2 = ISO- / iso1 = ISO)
const own = (r) => ((r.iso2 || '').toUpperCase().startsWith(ISO + '-')) || ((r.iso1 || '').toUpperCase() === ISO)
  || (ISO === 'GR' && /[\u0370-\u03FF]/.test(r.name || '')); // GR: rels sans ISO, filtre écriture grecque
const l2 = rels.filter(r => r.level === 2);
const own2 = l2.filter(own);
let n1rels;
if (ISO === 'GR') {
  // Grèce : OSM n'a PAS de peripheries iso- : silhouette = unités régionales L6
  // (littoraux détaillés) ; la relation L2 GR est trop simplifiée (116 ways).
  n1rels = rels.filter(r => r.level === 6 && (r.name || '').includes('Ενότητα'));
  process.stderr.write('GR: ' + n1rels.length + ' unités régionales\n');
  if (n1rels.length < 50) throw new Error('GR: unités régionales insuffisantes');
} else if (ISO === 'CY' ) {
  n1rels = rels.filter(r => N1.has(r.level) && own(r));
} else {
  n1rels = rels.filter(r => N1.has(r.level) && own(r));
}
process.stderr.write(ISO + ': ' + l2.length + ' rel L2 (' + own2.length + ' pays), ' + n1rels.length + ' rel n1 du pays\n');
const nom = own2.length ? own2[0].name : ISO;
let rings = [];
for (const r of n1rels) for (const ring of ringsForRelation(r)) rings.push(ring);
if (!rings.length) {
  process.stderr.write(ISO + ': PAS de n1 → fallback L2 directe\n');
  for (const r of own2) for (const ring of ringsForRelation(r)) rings.push(ring);
}
// annexes (micro-États inclus dans le pays voisin)
for (const a of ANNEX) {
  const mr = l2.filter(r => (r.iso1 || '').toUpperCase() === a.toUpperCase());
  for (const r of mr) {
    process.stderr.write(ISO + ': annexe ' + a + ' (rel ' + r.id + ' ' + r.name + ')\n');
    for (const ring of ringsForRelation(r)) rings.push(ring);
  }
}
let nWays = 0; for (const ring of rings) nWays += ring.length;
const out = { iso: ISO, nom, n: rings.length, rings };
fs.writeFileSync(OUTDIR + '/land9.json', JSON.stringify(out));
fs.writeFileSync(OUTDIR + '/land9.json.gz', zlib.gzipSync(Buffer.from(JSON.stringify(out)), { level: 9 }));
process.stderr.write(ISO + ': ' + rings.length + ' anneaux, ' + nWays + ' ways référencés\n');