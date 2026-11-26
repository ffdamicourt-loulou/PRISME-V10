#!/usr/bin/env node
// ways2bin.js — convertit out1/ways.json (JSON array plat) en fichiers binaires:
//   ids.bin (int64), off.bin (int64, n+1), refs.bin (int64 plat), coast.bin (uint8)
//   node ways2bin.js <dir_ways>
'use strict';
const fs = require('fs');
const DIR = process.argv[2];
const txt = fs.readFileSync(DIR + '/ways.json', 'utf8');
const re = /"id":(\d+),"refs":\[([0-9,]*)\]/g;
let cap = 1 << 20, nWays = 0;
let ids = new BigInt64Array(cap), offArr = new BigInt64Array(cap + 1);
let capR = 1 << 24; let refs = new BigInt64Array(capR); let nRefs = 0;
let coast = new Uint8Array(cap);
let m;
while ((m = re.exec(txt)) !== null) {
  const id = BigInt(m[1]);
  let lo = m.index, hi = re.lastIndex;
  // coast ? chercher '"natural":"coastline"' apres refs ] jusqu'a la fin de l'objet
  const seg = txt.slice(hi, txt.indexOf('},{', hi) < 0 ? txt.length : txt.indexOf('},{', hi));
  const c = seg.includes('"natural":"coastline"') ? 1 : 0;
  if (nWays === cap) {
    const nid = new BigInt64Array(cap * 2); nid.set(ids); ids = nid;
    const no = new BigInt64Array(cap * 2 + 1); no.set(offArr); offArr = no;
    const nc = new Uint8Array(cap * 2); nc.set(coast); coast = nc;
    cap *= 2;
  }
  const parts = m[2] ? m[2].split(',') : [];
  if (nRefs + parts.length > capR) {
    const nr = new BigInt64Array(Math.max(capR * 2, nRefs + parts.length)); nr.set(refs); refs = nr; capR = nr.length;
  }
  for (const p of parts) refs[nRefs++] = BigInt(p);
  ids[nWays] = id; coast[nWays] = c; offArr[nWays + 1] = BigInt(nRefs);
  nWays++;
  void lo; void hi;
}
fs.writeFileSync(DIR + '/eways_ids.bin', ids.subarray(0, nWays));
fs.writeFileSync(DIR + '/eways_off.bin', offArr.subarray(0, nWays + 1));
fs.writeFileSync(DIR + '/eways_refs.bin', refs.subarray(0, nRefs));
fs.writeFileSync(DIR + '/eways_coast.bin', coast.subarray(0, nWays));
console.log('ways2bin:', nWays, 'ways,', nRefs, 'refs,', Number(offArr[nWays]));
