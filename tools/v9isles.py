#!/usr/bin/env python
# v9isles.py — îles d'un pays en VECTORIEL (trait de côte OSM natif, pas de
# raster) : chaque île = cycle de ways natural=coastline correctement orienté.
#   python v9isles.py <ISO> [EPS_dp] [KEEP_frac] [min_km2]
# - assemblage des chaînes par continuité d'angle (pas de bulles : contrairement
#   au repaint raster, le remplissage suit EXACTEMENT le trait de côte OSM)
# - tri par aire, on garde KEEP_frac (65% par def = on supprime les 35% plus
#   petites) ; en plus aire min ~0.02 km² pour ecarter les cailloux
# - les paths sont AJOUTES au bloc out/final/<ISO>.json.gz (mode append : le
#   contour continental du bloc n'est pas touche)
import sys, gzip, json, math, os
import numpy as np
from collections import defaultdict

ISO = sys.argv[1] if len(sys.argv) > 1 else 'GR'
EPS = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0005
KEEP = float(sys.argv[3]) if len(sys.argv) > 3 else 0.65
import os
MIN_KM2 = float(sys.argv[4]) if len(sys.argv) > 4 else 0.02
# BOX (optionnel, argv5) : 'lon0,lon1,lat0,lat1' — hors-box = excl (ex FR metropole sans DOM)
BOX = None
if len(sys.argv) > 5 and sys.argv[5]:
    BOX = tuple(float(x) for x in sys.argv[5].split(','))
    if len(BOX) != 4: BOX = None

D = '/home/user/artifacts/v9/data/' + ISO + '/'
OUT = '/home/user/artifacts/v9/out/final/%s.json.gz' % ISO

def jload(p):
    with gzip.open(p) as f: return json.load(f)

ways = jload(D + 'ways.json.gz')
nodes = jload(D + 'nodes.json.gz')
_ids = np.asarray(nodes['ids'], dtype=np.int64)
_o = np.argsort(_ids); _ids = _ids[_o]
_lons = np.asarray(nodes['lons'], dtype=np.float64)[_o]
_lats = np.asarray(nodes['lats'], dtype=np.float64)[_o]
class _NM:
    def __getitem__(self, k):
        i = np.searchsorted(_ids, k)
        if i >= len(_ids) or _ids[i] != k: raise KeyError(k)
        return (_lons[i], _lats[i])
    def get(self, k, d=None):
        i = np.searchsorted(_ids, k)
        if i >= len(_ids) or _ids[i] != k: return d
        return (_lons[i], _lats[i])
    def __contains__(self, k):
        i = np.searchsorted(_ids, k)
        return i < len(_ids) and _ids[i] == k
nm = _NM()

# ways de cote avec refs resolvable au format [nodeIds]
cw = {}
for w in ways:
    if (w.get('tags') or {}).get('natural') != 'coastline': continue
    rl = [r for r in w['refs'] if r in nm]
    if len(rl) >= 2: cw[int(w['id'])] = rl

byEnd = defaultdict(list)
for wid, rl in cw.items():
    byEnd[rl[0]].append(wid)
    byEnd[rl[-1]].append(wid)

def head(wid, at):
    rl = cw[wid]
    return rl[1] if rl[0] == at else rl[-2]

def tail(wid, at):
    rl = cw[wid]
    return rl[-2] if rl[0] == at else rl[1]

used = set()
islands = []
# --- composantes du graphe des ways de cote (union-find sur les nodes d'extremite)
parent = {}
def find_(x):
    while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
    return x
def union_(a, b):
    ra, rb = find_(a), find_(b)
    if ra != rb: parent[ra] = rb
for wid in cw: parent[wid] = wid
adj = defaultdict(list)
for wid, rl in cw.items():
    adj[rl[0]].append(wid)
    adj[rl[-1]].append(wid)
for nd in adj:
    lst = adj[nd]
    for x in lst[1:]:
        union_(lst[0], x)
comps = defaultdict(list)
for wid in cw:
    comps[find_(wid)].append(wid)

def pipv(poly, PX, PY):
    # ray-cast vectorise (numpy) : poly lon/lat, PX/PY tableaux
    a = np.asarray(poly, dtype=float)
    x, y = a[:, 0], a[:, 1]
    x2, y2 = np.roll(x, -1), np.roll(y, -1)
    inside = np.zeros(PX.shape, dtype=bool)
    for i in range(len(x)):
        cond = (y[i] > PY) != (y2[i] > PY)
        with np.errstate(divide='ignore', invalid='ignore'):
            xint = (x2[i] - x[i]) * (PY - y[i]) / (y2[i] - y[i]) + x[i]
        inside ^= cond & (PX < xint)
    return inside

def pip(poly, px, py):
    return bool(pipv(poly, np.array([px]), np.array([py]))[0])

def hierholzer(comp_ways):
    ws = set(comp_ways)
    # degres : si exactement 2 nodes impairs (breche OSM), pont direct
    deg = defaultdict(int)
    for w in comp_ways:
        rl = cw[w]; deg[rl[0]] += 1; deg[rl[-1]] += 1
    odd = [n for n, d in deg.items() if d % 2 == 1]
    bridge = None
    if len(odd) == 2:
        a, b = odd
        bridge = True
        bridge_nodes = (a, b)
        adj[a].append(-1); adj[b].append(-1)
    st = [cw[comp_ways[0]][0]]
    out = []
    while st:
        v = st[-1]
        nxt = None
        for w in adj[v]:
            if w == -1:
                if bridge is not None: nxt = -1; break
                continue
            if w in ws:
                nxt = w; break
        if nxt == -1:
            bridge = None
            st.append(bridge_nodes[1] if st[-1] == bridge_nodes[0] else bridge_nodes[0])
        elif nxt is None:
            out.append(st.pop())
        else:
            ws.discard(nxt)
            rl = cw[nxt]
            if rl[0] == v: st.append(rl[-1])
            else: st.append(rl[0])
    if len(odd) == 2:
        try: adj[a].remove(-1); adj[b].remove(-1)
        except ValueError: pass
    if len(out) < 4 or out[0] != out[-1]: return None
    return out

def nodes_full(cycle_nodes):
    # re-inserer les nodes interieurs de chaque way dans l'ordre du cycle
    pts = []
    prev = None
    for a, b in zip(cycle_nodes, cycle_nodes[1:]):
        found = False
        for w in adj[a]:
            if w == -1: continue
            rl = cw[w]
            if rl[0] == a and rl[-1] == b: sq = rl
            elif rl[-1] == a and rl[0] == b: sq = rl[::-1]
            else: continue
            pts += sq if prev is None else sq[1:]
            prev = b; found = True; break
        if not found:
            # saut de pont (breche OSM) : on raccourcit par le node suivant
            if prev is None: return None
            pts.append(b); prev = b
    return pts

# --- exclusion du continent : le bloc final contient le path continental (ps[0]) ;
# toute boucle qui recouvre une maille interieure au continent est un doublon
# (Peleponnese coupe par le canal de Corinthe, etc.)
_main = []
try:
    _blk0 = jload(OUT)
    _s = _blk0['ps'][0].replace('Z', ' ').replace('M', ' ').replace('L', ' ').split()
    _main = [(float(_s[i]), float(_s[i + 1])) for i in range(0, len(_s), 2)]
except Exception as _e:
    print('ATTENTION: pas de path continental lisible:', _e)
from matplotlib.path import Path as MPath
INV = lambda y: math.degrees(math.atan(math.sinh(math.radians(y))))
if _main:
    _mlon = [p[0] for p in _main]; _mlat = [INV(p[1]) for p in _main]
    _mp = MPath([(p[0], INV(p[1])) for p in _main])
    _lon0, _lon1, _lat0, _lat1 = min(_mlon), max(_mlon), min(_mlat), max(_mlat)
    _gx = np.arange(_lon0, _lon1 + 0.05, 0.05)
    _gy = np.arange(_lat0, _lat1 + 0.05, 0.05)
    _GX, _GY = np.meshgrid(_gx, _gy)
    _inside_main = _mp.contains_points(np.column_stack([_GX.ravel(), _GY.ravel()])).reshape(_GX.shape)
    _main_samples = [(float(_GX[i, j]), float(_GY[i, j]))
                     for i, j in zip(*np.nonzero(_inside_main))]
    _MSX = np.array([q[0] for q in _main_samples]); _MSY = np.array([q[1] for q in _main_samples])
    print('echantillons interieur continental:', len(_main_samples))
else:
    _main_samples = []

def walk_chain(ws):
    # composante OUVERTE (2 nodes impairs = breche OSM) : marche directe des ways,
    # chemin complet a->b puis fermeture par la corde b->a
    deg = defaultdict(int)
    for w in ws:
        rl = cw[w]; deg[rl[0]] += 1; deg[rl[-1]] += 1
    odd = [n for n, d in deg.items() if d % 2 == 1]
    if len(odd) != 2: return None
    cur = odd[0]; seen = set(); pts = [cur]; wss = set(ws)
    while True:
        cand = [w for w in adj[cur] if w in wss and w not in seen]
        if not cand: break
        w = cand[0]; seen.add(w)
        rl = cw[w]
        seq = rl if rl[0] == cur else rl[::-1]
        pts += seq[1:]; cur = seq[-1]
    if cur != odd[1] or len(seen) != len(wss): return None
    pts.append(pts[0])   # fermeture par la corde
    return pts

import sys as _s, time as _t
_NCP = len(comps)
_done = [0]
def _progbump():
    _done[0] += 1
    if _done[0] % 500 == 0:
        print('scan %d/%d %.0fs' % (_done[0], _NCP, _t.time()-_T0), flush=True)
_T0 = _t.time()
for comp_ways in comps.values():
    pts = None
    if len(comp_ways) == 1:            # anneau : way circulaire unique (ile simple)
        rl = cw[comp_ways[0]]
        if rl[0] == rl[-1] and len(rl) >= 8: pts = list(rl)
    elif len(comp_ways) == 2:          # cycle de 2 ways partageant leurs extremites
        r1, r2 = cw[comp_ways[0]], cw[comp_ways[1]]
        if {r1[0], r1[-1]} == {r2[0], r2[-1]}:
            sq = r2 if r2[0] == r1[-1] else r2[::-1]
            pts = list(r1) + list(sq[1:]) + [r1[0]]
    if pts is None:
        ch = walk_chain(comp_ways)
        if ch is not None:
            pts = ch
        else:
            cyc = hierholzer(comp_ways)
            if cyc is None: continue
            pts = nodes_full(cyc)
    _progbump()
    if not pts or len(pts) < 8 or pts[0] != pts[-1]: continue
    ll = [nm[p] for p in pts]
    if BOX:
        lo0 = min(q[0] for q in ll); lo1 = max(q[0] for q in ll)
        la0 = min(q[1] for q in ll); la1 = max(q[1] for q in ll)
        if BOX[0] > lo0 and BOX[1] < lo1 and (lo0+lo1)/2 >= BOX[1]: continue
        if (lo0+lo1)/2 < BOX[0] or (lo0+lo1)/2 > BOX[1] or (la0+la1)/2 < BOX[2] or (la0+la1)/2 > BOX[3]:
            continue
    if _main_samples:
        lo = [q[0] for q in ll]; la = [q[1] for q in ll]
        MX = np.asarray(lo); MY_ = np.asarray(la)
        _lk = (_MSX >= MX.min()) & (_MSX <= MX.max()) & (_MSY >= MY_.min()) & (_MSY <= MY_.max())
        _ii = np.nonzero(_lk)[0]
        if len(_ii) > 400: _ii = _ii[::max(1, len(_ii) // 400)]
        cand = [(_MSX[k], _MSY[k]) for k in _ii]
        if cand:
            cx = np.array([c[0] for c in cand]); cy = np.array([c[1] for c in cand])
            if len(ll) > 20000:
                inside_any = MPath(np.array(ll)).contains_points(np.column_stack([cx, cy])).any()
            else:
                inside_any = pipv(ll, cx, cy).any()
            if inside_any:
                continue  # recouvre le continent deja trace
    islands.append(pts)
print('chaines fermees:', len(islands))
MY = lambda la: math.degrees(math.asinh(math.tan(math.radians(la))))

def area_km2(lonlat):
    a = np.array(lonlat, dtype=float)
    x = np.radians(a[:, 0]) * np.cos(np.radians((a[:, 1].max() + a[:, 1].min()) / 2))
    y = a[:, 1]
    s = abs(np.sum((np.roll(x, -1) - x) * (y + np.roll(y, -1)))) / 2
def shoelace_km2(lonlat):
    a = np.array(lonlat, dtype=float)
    lat0 = math.radians((a[:, 1].max() + a[:, 1].min()) / 2)
    x = a[:, 0] * 111.32 * math.cos(lat0)
    y = a[:, 1] * 110.57
    s = abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2
    return s

def dp_simplify(pts, eps):
    n = len(pts)
    if n < 3: return pts
    keep = np.zeros(n, dtype=bool); keep[0] = keep[-1] = True
    stk = [(0, n - 1)]
    while stk:
        a, b = stk.pop()
        if b <= a + 1: continue
        pa, pb = pts[a], pts[b]
        m = pts[a + 1:b]
        e = pb - pa
        L2v = e[0] * e[0] + e[1] * e[1]
        if L2v == 0: dist = np.hypot(*(m - pa).T)
        else:
            t = np.clip(((m - pa) @ e) / L2v, 0, 1)
            proj = pa + t[:, None] * e
            dist = np.hypot(*(m - proj).T)
        k = int(np.argmax(dist))
        if dist[k] > eps:
            kk = a + 1 + k
            keep[kk] = True
            stk.append((a, kk)); stk.append((kk, b))
    return pts[keep]

scored = []
MONSTRES = 0
for pts in islands:
    km2 = shoelace_km2([nm[p] for p in pts])
    if km2 >= MIN_KM2 and km2 <= int(os.environ.get('MONSTER', '60000')):
        scored.append((km2, pts))
    elif km2 > int(os.environ.get('MONSTER', '60000')): MONSTRES += 1
print('monstres rejetes (>60000 km2):', MONSTRES)
scored.sort(key=lambda t: -t[0])
nkeep = max(1, int(round(KEEP * len(scored))))
scored = scored[:nkeep]
print('iles gardees: %d / %d (aire total %.0f km²)' % (len(scored), nkeep, sum(s[0] for s in scored)))

ps = []
tot = 0
for km2, pts in scored:
    m = np.array([[nm[p][0], MY(nm[p][1])] for p in pts])
    m = dp_simplify(m, EPS)
    if len(m) < 4: continue
    d = ''
    for k, p in enumerate(m):
        d += ('M' if k == 0 else 'L') + str(round(float(p[0]), 5)) + ' ' + str(round(float(p[1]), 5))
        tot += 1
    ps.append(d + 'Z')

blk = jload(OUT)
blk.setdefault('ps', []).extend(ps)
blk['boucles'] = len(blk['ps'])
blk['pts'] = blk.get('pts', 0) + tot
blk['iles'] = len(ps)
blk['methode'] = blk.get('methode', '') + '+iles'
with gzip.open(OUT, 'wb') as f:
    f.write(json.dumps(blk).encode())
print('bloc %s: +%d iles, +%d pts ; total boucles %d' % (ISO, len(ps), tot, blk['boucles']))