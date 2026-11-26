#!/usr/bin/env node
// v8 extract.js — lecteur PBF OSM autonome (stdlib seule), 3 passes.
//   node extract.js <pbf> <outdir> <levels CSV> <1|2|3>
// p1: relations admin (type=boundary & boundary=administrative) -> rels.json
// p2: ways membres -> ways.json ; p3: nodes -> nodes.json
'use strict';
const fs = require('fs');
const zlib = require('zlib');
const [PBF, OUTDIR, LEVELS, PHASE] = process.argv.slice(2);
const WANT = new Set(LEVELS.split(',').map(Number));
const levelNames = { 2: 'pays', 4: 'region', 6: 'dept' };

/* ---- protobuf bas niveau ---- */
function rdU32(b, p) { return (b[p] | b[p+1]<<8 | b[p+2]<<16) + b[p+3]*0x100000000; } // non signé
function varint(b, p) {
  let v = 0, s = 0, q = p;
  for (;;) { const x = b[q++]; v += (x & 0x7f) * Math.pow(2, s); if (!(x & 0x80)) break; s += 7; if (s > 63) { v = v + (x&0x7f)*Math.pow(2,s); break; } }
  return [v >>> 0 === v && v < Number.MAX_SAFE_INTEGER ? v : v, q];
}
function varintBig(b, p) { // retourne BigInt pour valeurs > 2^53 ? ici ids OSM < 2^53, ok avec Number
  return varint(b, p);
}
function zz(v) { return (v % 2 === 1) ? -(v + 1) / 2 : v / 2; } // attention v peut depasser 32 bits -> utiliser la version 64
function zz64(v) { return (v & 1) ? -(BigInt(v >> 1) + 1n) : BigInt(v >> 1); }
function packed(b, p) { const [n, q] = varint(b, p); return [q, q + Number(n)]; }
function strfield(b, p, end) { const [n, q] = varint(b, p); return b.slice(q, q + n).toString('utf8'); }

/* ---- lecture des blobs ---- */
function* blocks(path) {
  const fd = fs.openSync(path, 'r');
  const st = fs.statSync(path);
  const H = Buffer.alloc(4);
  let pos = 0;
  const CH = 64 * 1024 * 1024;
  let buf = Buffer.alloc(0);
  while (pos < st.size) {
    fs.readSync(fd, H, 0, 4, pos); pos += 4;
    const hs = H.readUInt32BE(0);
    const hb = Buffer.alloc(hs);
    fs.readSync(fd, hb, 0, hs, pos); pos += hs;
    // BlobHeader: 1=type(str) 3=datasize(varint)
    let p = 0, type = '', datasize = 0;
    while (p < hb.length) {
      const tag = hb[p++], f = tag >> 3, wt = tag & 7;
      if (f === 1 && wt === 2) { const [n, q] = varint(hb, p); type = hb.slice(q, q + n).toString('utf8'); p = q + n; }
      else if (f === 3 && wt === 0) { [datasize, p] = varint(hb, p); }
      else if (wt === 0) { [, p] = varint(hb, p); }
      else if (wt === 2) { const [n, q] = varint(hb, p); p = q + n; }
      else if (wt === 5) p += 4; else if (wt === 1) p += 8; else throw new Error('blobheader wt ' + wt);
    }
    const bb = Buffer.alloc(datasize);
    fs.readSync(fd, bb, 0, datasize, pos); pos += datasize;
    // Blob: 1=raw 2=zlib_data
    let raw = null; p = 0;
    while (p < bb.length) {
      const tag = bb[p++], f = tag >> 3, wt = tag & 7;
      if (wt === 2) { const [n, q] = varint(bb, p); const d = bb.slice(q, q + n); if (f === 1) raw = d; else if (f === 3) raw = zlib.inflateSync(d); p = q + n; }
      else if (wt === 0) { [, p] = varint(bb, p); }
      else if (wt === 5) p += 4; else if (wt === 1) p += 8; else throw new Error('blob wt ' + wt);
    }
    yield { type, raw };
  }
  fs.closeSync(fd);
}
/* ---- PrimitiveBlock ---- */
function parseBlock(raw) {
  let p = 0;
  let stringtable = null, granularity = 100, lat_offset = 0n, lon_offset = 0n;
  const groups = [];
  while (p < raw.length) {
    const tag = raw[p++], f = tag >> 3, wt = tag & 7;
    if (f === 1 && wt === 2) { // stringtable
      const [n, q] = varint(raw, p); const st = raw.slice(q, q + n); p = q + n;
      const s = []; let sp = 0;
      while (sp < st.length) { const t = st[sp++], wt2 = t & 7; /* field 1 bytes */ const [ln, sq] = varint(st, sp); s.push(st.slice(sq, sq + ln).toString('utf8')); sp = sq + ln; }
      stringtable = s;
    } else if (f === 2 && wt === 2) { // primitivegroup
      const [n, q] = varint(raw, p); groups.push(raw.slice(q, q + n)); p = q + n;
    } else if (f === 16 && wt === 0) { [granularity, p] = varint(raw, p); }
    else if (f === 17 && wt === 0) { // lat_offset int64 — assembler en BigInt
      let v = 0n, sh = 0n; for (;;) { const x = raw[p++]; v |= BigInt(x & 0x7f) << sh; if (!(x & 0x80)) break; sh += 7n; } lat_offset = v;
    } else if (f === 18 && wt === 0) {
      let v = 0n, sh = 0n; for (;;) { const x = raw[p++]; v |= BigInt(x & 0x7f) << sh; if (!(x & 0x80)) break; sh += 7n; } lon_offset = v;
    } else if (wt === 0) { [, p] = varint(raw, p); }
    else if (wt === 2) { const [n, q] = varint(raw, p); p = q + n; }
    else if (wt === 5) p += 4; else if (wt === 1) p += 8; else throw new Error('pb wt ' + wt + ' f ' + f);
  }
  if (!stringtable) throw new Error('pas de stringtable');
  return { stringtable, groups, granularity, lat_offset, lon_offset };
}
/* ---- DenseNodes ---- */
function* denseNodes(group) {
  // PrimitiveGroup: champ 2 = DenseNodes
  let dn = null, p = 0;
  while (p < group.length) {
    const tag = group[p++], f = tag >> 3, wt = tag & 7;
    if (f === 2 && wt === 2) { const [n, q] = varint(group, p); dn = group.slice(q, q + n); p = q + n; }
    else if (wt === 2) { const [n, q] = varint(group, p); p = q + n; }
    else if (wt === 0) { [, p] = varint(group, p); }
    else if (wt === 5) p += 4; else if (wt === 1) p += 8; else throw new Error('pg wt ' + wt);
  }
  if (!dn) return;
  let ids = null, lats = null, lons = null;
  p = 0;
  while (p < dn.length) {
    const tag = dn[p++], f = tag >> 3, wt = tag & 7;
    if (f === 1 && wt === 2) { [p, ids] = packedSint(dn, p); }
    else if (f === 8 && wt === 2) { [p, lats] = packedSint(dn, p); }
    else if (f === 9 && wt === 2) { [p, lons] = packedSint(dn, p); }
    else if (wt === 2) { const [n, q] = varint(dn, p); p = q + n; }
    else if (wt === 0) { [, p] = varint(dn, p); }
    else if (wt === 5) p += 4; else if (wt === 1) p += 8; else throw new Error('dn wt ' + wt);
  }
  if (!ids) return;
  let id = 0, la = 0, lo = 0;
  for (let i = 0; i < ids.length; i++) {
    id += Number(ids[i]); la += Number(lats[i]); lo += Number(lons[i]);
    yield { id, lat: la, lon: lo };
  }
}
function packedSint(buf, p) { // packed sint64 zigzag — decodage Number (pas de BigInt: OOM sur les gros PBF)
  const [n, q] = varint(buf, p); const end = q + Number(n);
  const out = [];
  let pp = q;
  while (pp < end) {
    let v = 0, sh = 0;
    for (;;) { const x = buf[pp++]; v += (x & 0x7f) * Math.pow(2, sh); if (!(x & 0x80)) break; sh += 7; }
    const s = (v % 2 === 1) ? -((v - 1) / 2 + 1) : v / 2;
    out.push(s);
  }
  return [pp, out];
}
function packedVarint(buf, p) {
  const [n, q] = varint(buf, p); const end = q + Number(n);
  const out = []; let pp = q;
  while (pp < end) { let v = 0n, sh = 0n; for (;;) { const x = buf[pp++]; v |= BigInt(x & 0x7f) << sh; if (!(x & 0x80)) break; sh += 7n; } out.push(v); }
  return [pp, out];
}
/* ---- Way / Relation ---- */
function waysInTagged(group, S) {
  const out = [];
  let p = 0;
  while (p < group.length) {
    const tag = group[p++], f = tag >> 3, wt = tag & 7;
    if (f === 3 && wt === 2) { // way
      const [n, q] = varint(group, p); out.push(group.slice(q, q + n)); p = q + n;
    } else if (wt === 2) { const [n, q] = varint(group, p); p = q + n; }
    else if (wt === 0) { [, p] = varint(group, p); }
    else if (wt === 5) p += 4; else if (wt === 1) p += 8; else throw new Error('grp wt ' + wt);
  }
  const res = [];
  for (const wb of out) {
    let id = 0n, refs = null; let pp = 0;
    let keys = null, vals = null;
    while (pp < wb.length) {
      const tag = wb[pp++], f = tag >> 3, wt = tag & 7;
      if (f === 1 && wt === 0) { let v = 0n, sh = 0n; for (;;) { const x = wb[pp++]; v |= BigInt(x & 0x7f) << sh; if (!(x & 0x80)) break; sh += 7n; } id = v; }
      else if (f === 2 && wt === 2) { [pp, keys] = packedVarint(wb, pp); }
      else if (f === 3 && wt === 2) { [pp, vals] = packedVarint(wb, pp); }
      else if (f === 8 && wt === 2) { [pp, refs] = packedSint(wb, pp); }
      else if (wt === 0) { [, pp] = varint(wb, pp); }
      else if (wt === 2) { const [n, q] = varint(wb, pp); pp = q + n; }
      else if (wt === 5) pp += 4; else if (wt === 1) pp += 8; else throw new Error('way wt ' + wt);
    }
    refs = refs || [];
    const refsN = []; let acc = 0n;
    for (const d of refs) { acc += BigInt(d); refsN.push(Number(acc)); }
    const tags = {};
    if (keys) for (let i = 0; i < keys.length; i++) {
      const k = S[Number(keys[i])], v = S[Number(vals[i])];
      if (k === 'natural' || k === 'maritime' || k === 'name' || k === 'name:fr') tags[k] = v;
    }
    res.push({ id: Number(id), refs: refsN, tags });
  }
  return res;
}
function relationsIn(group, S) {
  const out = [];
  let p = 0;
  while (p < group.length) {
    const tag = group[p++], f = tag >> 3, wt = tag & 7;
    if (f === 4 && wt === 2) { const [n, q] = varint(group, p); out.push(group.slice(q, q + n)); p = q + n; }
    else if (wt === 2) { const [n, q] = varint(group, p); p = q + n; }
    else if (wt === 0) { [, p] = varint(group, p); }
    else if (wt === 5) p += 4; else if (wt === 1) p += 8; else throw new Error('grp wt ' + wt);
  }
  const res = [];
  for (const rb of out) {
    let id = 0n, keys = null, vals = null, roles = null, memids = null, types = null;
    let pp = 0;
    while (pp < rb.length) {
      const tag = rb[pp++], f = tag >> 3, wt = tag & 7;
      if (f === 1 && wt === 0) { let v = 0n, sh = 0n; for (;;) { const x = rb[pp++]; v |= BigInt(x & 0x7f) << sh; if (!(x & 0x80)) break; sh += 7n; } id = v; }
      else if (f === 2 && wt === 2) { [pp, keys] = packedVarint(rb, pp); }
      else if (f === 3 && wt === 2) { [pp, vals] = packedVarint(rb, pp); }
      else if (f === 8 && wt === 2) { [pp, roles] = packedVarint(rb, pp); }
      else if (f === 9 && wt === 2) { [pp, memids] = packedSint(rb, pp); }
      else if (f === 10 && wt === 2) { [pp, types] = packedVarint(rb, pp); }
      else if (wt === 0) { [, pp] = varint(rb, pp); }
      else if (wt === 2) { const [n, q] = varint(rb, pp); pp = q + n; }
      else if (wt === 5) pp += 4; else if (wt === 1) pp += 8; else throw new Error('rel wt ' + wt + ' f ' + f);
    }
    keys = keys || []; vals = vals || []; roles = roles || []; memids = memids || []; types = types || [];
    const tags = {};
    for (let i = 0; i < keys.length; i++) tags[S[Number(keys[i])]] = S[Number(vals[i])];
    const members = []; let acc = 0n;
    for (let i = 0; i < memids.length; i++) {
      acc += BigInt(memids[i]);
      members.push({ t: Number(types[i]), id: Number(acc), role: S[Number(roles[i])] });
    }
    res.push({ id: Number(id), tags, members });
  }
  return res;
}
/* ---- passe ---- */
const t00 = Date.now();
function log(...a) { console.error(new Date().toISOString().slice(11, 19), ...a); }
if (PHASE === '1') {
  const rels = [];
  for (const b of blocks(PBF)) {
    if (b.type !== 'OSMData') continue;
    const PB = parseBlock(b.raw);
    for (const g of PB.groups) {
      for (const r of relationsIn(g, PB.stringtable)) {
        const t = r.tags;
        if (t.type !== 'boundary' || t.boundary !== 'administrative') continue;
        const al = parseInt(t.admin_level);
        if (!WANT.has(al)) continue;
        rels.push({ id: r.id, level: al, name: t.name || t['name:fr'] || '', iso1: t['ISO3166-1'] || t.ISO3166_1 || '', iso2: t['ISO3166-2'] || t.ISO3166_2 || '', members: r.members.map(m => ({ t: m.t, id: m.id, role: m.role })) });
      }
    }
    if (rels.length && rels.length % 50000 === 0) log('rels', rels.length);
  }
  fs.writeFileSync(OUTDIR + '/rels.json', JSON.stringify(rels));
  const c = {}; for (const r of rels) c[r.level] = (c[r.level] || 0) + 1;
  log('Ecrites', rels.length, 'relations', JSON.stringify(c), ((Date.now()-t00)/1000).toFixed(0) + 's');
} else if (PHASE === '2') {
  const rels = JSON.parse(fs.readFileSync(OUTDIR + '/rels.json', 'utf8'));
  const need = new Set();
  for (const r of rels) for (const m of r.members) if (m.t === 1) need.add(m.id);
  log('ways recherchees:', need.size);
  const ways = []; let scanned = 0;
  for (const b of blocks(PBF)) {
    if (b.type !== 'OSMData') continue;
    const PB = parseBlock(b.raw);
    for (const g of PB.groups) {
      for (const w of waysInTagged(g, PB.stringtable)) { scanned++; if (need.has(w.id) || (w.tags && w.tags.natural === 'coastline' && w.refs.length >= parseInt(process.env.NREFT || '0'))) ways.push(w); }
    }
  }
  fs.writeFileSync(OUTDIR + '/ways.json', JSON.stringify(ways));
  log('ways scannees', scanned, 'gardees', ways.length, ((Date.now()-t00)/1000).toFixed(0) + 's');
} else if (PHASE === '3') {
  const wtxt = fs.readFileSync(OUTDIR + '/ways.json', 'utf8'); // texte brut, PAS JSON.parse (memoire x12)
  let cnt = 0;
  const needL = [];
  let last = 0;
  while (true) {
    const i = wtxt.indexOf('"refs":[', last);
    if (i < 0) break;
    const j = wtxt.indexOf(']', i);
    const arr = wtxt.slice(i + 8, j);
    for (const s of arr.split(',')) if (s) needL.push(Number(s));
    last = j;
  }
  const need = Float64Array.from(needL);
  needL.length = 0;
  need.sort();
  const has = (id) => { let lo = 0, hi = need.length - 1;
    while (lo <= hi) { const m = (lo + hi) >> 1; const v = need[m];
      if (v === id) return true; if (v < id) lo = m + 1; else hi = m - 1; }
    return false; };
  log('nodes recherches:', need.length);
  const ids = [], lons = [], lats = [];
  let scanned = 0;
  for (const b of blocks(PBF)) {
    if (b.type !== 'OSMData') continue;
    const PB = parseBlock(b.raw);
    const g = PB.granularity, LO = PB.lon_offset, LA = PB.lat_offset;
    for (const gr of PB.groups) {
      for (const n of denseNodes(gr)) {
        scanned++;
        if (!has(Number(n.id))) continue;
        ids.push(n.id);
        lons.push(1e-9 * (g * n.lon + Number(LO)));
        lats.push(1e-9 * (g * n.lat + Number(LA)));
      }
    }
    if (scanned % 20000000 === 0) log('nodes', (scanned/1e6).toFixed(0) + 'M, gardes', ids.length);
  }
  fs.writeFileSync(OUTDIR + '/nodes.json', JSON.stringify({ ids, lons, lats }));
  log('nodes scannes', scanned, 'gardes', ids.length, ((Date.now()-t00)/1000).toFixed(0) + 's');
} else throw new Error('phase ?');