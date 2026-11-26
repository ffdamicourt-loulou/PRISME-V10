#!/usr/bin/env node
// v9html.js — assemble la carte de VÉRIFICATION v9 (niveau pays uniquement)
// à partir des blocs out/blocks/*.json.gz → europe-v9-test.html
'use strict';
const fs = require('fs');
const DIR = '/home/user/artifacts/v9/out/final';
const OUT = process.argv[2] || '/home/user/artifacts/v9/out/europe-v9-test.html';
const isos = fs.readdirSync(DIR).filter(f => f.endsWith('.json.gz')).map(f => f.slice(0, -8)).sort();
let X0 = 1e9, Y0 = 1e9, X1 = -1e9, Y1 = -1e9;
const blocks = [];
for (const iso of isos) {
  const t = fs.readFileSync(DIR + '/' + iso + '.json.gz').toString('base64');
  blocks.push({ iso, b64: t });
}
// bbox : lire le début décompressé de chaque bloc (b est court après d ? non, b est APRÈS d)
// → plutôt recalculer depuis metadata stockées : on relit le json entier (max ~30 Mo, ok)
const zlib = require('zlib');
for (const iso of isos) {
  const j = JSON.parse(zlib.gunzipSync(fs.readFileSync(DIR + '/' + iso + '.json.gz')).toString());
  const [x0, y0, x1, y1] = [j.b[0], j.b[1], j.b[2], j.b[3]];
  X0 = Math.min(X0, x0); Y0 = Math.min(Y0, y0); X1 = Math.max(X1, x1); Y1 = Math.max(Y1, y1);
}
console.log('bbox', X0.toFixed(2), Y0.toFixed(2), X1.toFixed(2), Y1.toFixed(2), '| pays:', blocks.length);
const HO = fs.createWriteStream(OUT, { highWaterMark: 1 << 22 });
HO.write('<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><title>Prisme v9 — Europe</title>\n<style>html,body{margin:0;height:100%;font-family:system-ui,sans-serif;background:#eef3fb}\n#map{width:100vw;height:100vh;display:block;touch-action:none}\n#ui{position:fixed;top:10px;left:10px;background:#fff;border-radius:10px;padding:10px 14px;box-shadow:0 2px 10px rgba(0,0,0,.18);font-size:14px;max-width:340px}\n#info{margin-top:6px;color:#333;min-height:18px}\n\n#map g.z:hover path.f{fill:orange;stroke:orange}\n</style></head><body>\n<svg id="map" xmlns="http://www.w3.org/2000/svg"></svg>\n<div id="ui"><div id="titre"><b>Prisme v9 — vérification</b></div><div id="info">Chargement…</div><div style="margin-top:4px;color:#666">molette : zoom · glisser : déplacer · survol : nom (français)</div></div>\n');
blocks.forEach((bl, i) => { HO.write('<script id="blk' + i + '" type="application/gzip-base64">' + bl.b64 + '</script>\n'); });
HO.write(`<script>
const INFO=document.getElementById('info');
const T=new Int8Array(128).fill(-1);
"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/".split("").forEach((c,i)=>T[c.charCodeAt(0)]=i);
async function gunzipBlock(id){
 const b64=document.getElementById(id).textContent.trim();
 let n=b64.length;while(b64.charCodeAt(n-1)===61)n--;
 const out=new Uint8Array((n*3)>>2);
 let acc=0,nb=0,op=0;
 for(let i=0;i<n;i++){const v=T[b64.charCodeAt(i)];if(v<0)continue;acc=(acc<<6)|v;nb+=6;if(nb>=8){nb-=8;out[op++]=(acc>>>nb)&255;}}
 const ds=new DecompressionStream('gzip');
 const buf=await new Response(new Blob([out]).stream().pipeThrough(ds)).arrayBuffer();
 return new TextDecoder().decode(buf);
}
const MAP=document.getElementById('map');
const FRN={AL:'Albanie',AT:'Autriche',BA:'Bosnie-Herzégovine',BE:'Belgique',BG:'Bulgarie',BY:'Biélorussie',CH:'Suisse',CY:'Chypre',CZ:'Tchéquie',DE:'Allemagne',DK:'Danemark',EE:'Estonie',ES:'Espagne',FI:'Finlande',FR:'France',GB:'Royaume-Uni',GR:'Grèce',HR:'Croatie',HU:'Hongrie',IE:'Irlande',IS:'Islande',IT:'Italie',LI:'Liechtenstein',LT:'Lituanie',LU:'Luxembourg',LV:'Lettonie',MD:'Moldavie',ME:'Monténégro',MK:'Macédoine du Nord',MT:'Malte',NL:'Pays-Bas',NO:'Norvège',PL:'Pologne',PT:'Portugal',RO:'Roumanie',RS:'Serbie',SE:'Suède',SI:'Slovénie',SK:'Slovaquie',UA:'Ukraine',XK:'Kosovo'};
const N=${blocks.length};
let VB=null,countries=null;
function fit(){const b=${JSON.stringify([X0, Y0, X1, Y1])};
 const w0=b[2]-b[0],h0=b[3]-b[1];
 const vasp=innerWidth/innerHeight,asp=w0/h0;const y0=-b[3];
 if(asp<vasp){const cx=(b[0]+b[2])/2,w=h0*vasp;VB=[cx-w/2,y0,w,h0];}else VB=[b[0],y0,w0,w0/vasp];
 MAP.setAttribute('viewBox',VB.join(' '));}
function draw(){
 let inner='';
 for(const c of countries){
  // NIVEAU 1 SEUL : le tracé du pays est DISSOUS (les régions ont disparu :
  // ways internes supprimés puis arêtes externes rechaînées en boucles fermées).
  // Une seule géométrie par pays : remplissage gris (avec liseré gris ~1px qui
  // referme les interstices) + trait blanc fin par-dessus = frontières et côtes.
  const nomFR = FRN[c.iso] || c.nom;
  let fl=''; const d=c.ps.join('');
  for(const p of c.ps) fl+='<path class="f" d="'+p+'"/>';   // UN PATH PAR BOUCLE (lecon v8)
  inner+='<g class="z" data-n="'+nomFR+'">'
   +'<g fill="#808080" stroke="none" stroke-width="0" stroke-linejoin="round">'+fl+'</g>'
   +'<path class="c" d="'+d+'" fill="none" stroke="#fff" stroke-width="0.005" stroke-linejoin="round"/>'
   +'<title>'+c.nom+'</title></g>';
 }
 MAP.innerHTML='<g id="flip" transform="scale(1,-1)">'+inner+'</g>';
 INFO.textContent=countries.length+' pays affichés';
 MAP.querySelectorAll('g.z').forEach(g=>{g.addEventListener('pointerenter',()=>{INFO.textContent=g.dataset.n;});});
}
MAP.addEventListener('wheel',e=>{e.preventDefault();const f=e.deltaY>0?1.25:0.8;
 const[x,y,w,h]=VB;const mx=x+(e.clientX/innerWidth)*w,my=y+(e.clientY/innerHeight)*h;
 VB=[mx-(mx-x)*f,my-(my-y)*f,w*f,h*f];MAP.setAttribute('viewBox',VB.join(' '));},{passive:false});
let dr=false,px=0,py=0;
MAP.addEventListener('pointerdown',e=>{dr=true;px=e.clientX;py=e.clientY;MAP.setPointerCapture(e.pointerId);});
MAP.addEventListener('pointermove',e=>{if(!dr)return;const[x,y,w,h]=VB;
 VB=[x-(e.clientX-px)/innerWidth*w,y-(e.clientY-py)/innerHeight*h,w,h];
 px=e.clientX;py=e.clientY;MAP.setAttribute('viewBox',VB.join(' '));});
MAP.addEventListener('pointerup',()=>dr=false);
(async()=>{
 const t0=performance.now();
 try{
  countries=[];
  for(let i=0;i<N;i++){
   INFO.textContent='Chargement pays '+(i+1)+'/'+N+'…';
   const blk=JSON.parse(await gunzipBlock('blk'+i));
   countries.push(blk);
   await new Promise(r=>setTimeout(r,5));
  }
  INFO.textContent='Dessin…';
  await new Promise(r=>setTimeout(r,30));
  fit();draw();
  document.getElementById('titre').innerHTML='<b>Prisme v9 — vérification</b><br><span style="color:#777">'+countries.length+' pays · level 1 · OSM/Geofabrik</span>';
  INFO.textContent='Prêt en '+Math.round(performance.now()-t0)+' ms';
 }catch(e){INFO.textContent='ERREUR: '+(e&&e.message?e.message:e);console.error(e);}
})();
</script></body></html>`);
HO.end(() => console.log('écrit', OUT, (fs.statSync(OUT).size / 1e6).toFixed(1), 'Mo'));
