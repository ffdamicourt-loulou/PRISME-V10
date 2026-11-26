#!/usr/bin/env node
// v9render.js — rendu PNG de preuve (région baltique) depuis les blocs finaux.
// Scanline nonzero + encodeur PNG minimal (zlib). Usage: node v9render.js
'use strict';
const fs = require('fs'), zlib = require('zlib'), path = require('path');
const V9 = '/home/user/artifacts/v9';
const ylat = y => Math.atan(Math.sinh(y * Math.PI / 180)) * 180 / Math.PI;

// zone de rendu (lon/lat)
const X0 = 20.6, X1 = 31.6, L0 = 54.9, L1 = 60.7;
const W = 1400, H = 900;
const COLORS = { LV: [86,160,90], EE: [70,120,220], RU: [200,90,70], LT: [160,120,200], BY: [220,170,60], FI: [60,180,200], default: [128,128,128] };

const files = fs.readdirSync(path.join(V9, 'out/final')).filter(f => f.endsWith('.json.gz'));
const rings = []; // {iso, r:[[lon,lat]], x0,x1}
for (const f of files) {
  const iso = f.slice(0, 2);
  const b = JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(V9, 'out/final', f))).toString());
  for (const d of b.ps) {
    const r = d.slice(1).split('L').map(s => s.split(' ').map(Number)).map(([x, y]) => [x, ylat(y)]);
    let x0 = 1e9, x1 = -1e9;
    for (const p of r) { if (p[0] < x0) x0 = p[0]; if (p[0] > x1) x1 = p[0]; }
    if (x1 < X0 || x0 > X1) continue;
    rings.push({ iso, r, x0, x1 });
  }
}
console.log('anneaux dans la zone:', rings.length);

const img = Buffer.alloc(W * H * 3, 255); // blanc
for (let py = 0; py < H; py++) {
  const lat = L1 - (L1 - L0) * (py + 0.5) / H;
  const spans = []; // {x, dw, iso}
  for (const { iso, r, x0, x1 } of rings) {
    if (x1 < X0 || x0 > X1) continue;
    const n = r.length;
    for (let i = 0; i < n; i++) {
      const a = r[i], b = r[(i + 1) % n];
      if ((a[1] <= lat && b[1] > lat) || (b[1] <= lat && a[1] > lat)) {
        const t = (lat - a[1]) / (b[1] - a[1]);
        spans.push({ x: a[0] + t * (b[0] - a[0]), dw: b[1] > a[1] ? 1 : -1, iso });
      }
    }
  }
  if (!spans.length) continue;
  spans.sort((p, q) => p.x - q.x);
  // nonzero: accumulate
  const wsum = new Map();
  let idx = 0;
  const active = []; // {iso, w} stacking — simplif: recompute from spans
  while (idx < spans.length) {
    const x = spans[idx].x;
    // process all spans at ~same x
    while (idx < spans.length && Math.abs(spans[idx].x - x) < 1e-9) {
      const s = spans[idx];
      wsum.set(s.iso, (wsum.get(s.iso) || 0) + s.dw);
      idx++;
    }
    const x2 = idx < spans.length ? spans[idx].x : X1 + 1;
    if (x2 <= X0 || x >= X1) continue;
    // paint span [x,x2] with the color of any iso with w!=0
    let col = null;
    for (const [iso, w] of wsum) if (w !== 0) { col = COLORS[iso] || COLORS.default; break; }
    if (!col) continue;
    const px1 = Math.max(0, Math.floor((x - X0) / (X1 - X0) * W));
    const px2 = Math.min(W - 1, Math.ceil((x2 - X0) / (X1 - X0) * W));
    const off = py * W * 3;
    for (let px = px1; px <= px2; px++) {
      const o = off + px * 3;
      img[o] = col[0]; img[o + 1] = col[1]; img[o + 2] = col[2];
    }
  }
}
console.log('raster OK');

// --- PNG encode (RGB, filter 0) ---
const crcT = new Int32Array(256);
for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; crcT[n] = c; }
const crc = buf => { let c = -1; for (const b of buf) c = crcT[(c ^ b) & 255] ^ (c >>> 8); return (c ^ -1) >>> 0; };
const chunk = (type, data) => {
  const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
  const td = Buffer.concat([Buffer.from(type), data]);
  const crcB = Buffer.alloc(4); crcB.writeUInt32BE(crc(td));
  return Buffer.concat([len, td, crcB]);
};
const ihdr = Buffer.alloc(13);
ihdr.writeUInt32BE(W, 0); ihdr.writeUInt32BE(H, 4);
ihdr[8] = 8; ihdr[9] = 2; // 8-bit RGB
const raw = Buffer.alloc(H * (W * 3 + 1));
for (let y = 0; y < H; y++) { raw[y * (W * 3 + 1)] = 0; img.copy(raw, y * (W * 3 + 1) + 1, y * W * 3, (y + 1) * W * 3); }
const png = Buffer.concat([
  Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
  chunk('IHDR', ihdr),
  chunk('IDAT', zlib.deflateSync(raw, { level: 6 })),
  chunk('IEND', Buffer.alloc(0))
]);
fs.writeFileSync('/home/user/artifacts/v9/out/apercu-baltique-41.png', png);
console.log('PNG écrit:', png.length, 'octets — apercu-baltique-41.png');
