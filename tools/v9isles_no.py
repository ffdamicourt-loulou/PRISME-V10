#!/usr/bin/env python
# v9isles_no.py — variante v9isles.py pour PACKAGES GEANTS (NO) : charge les
# ways de cote depuis les binaires ways2bin (ids/off/refs/coast) et les nodes
# depuis nodes.npz, jamais de JSON de 7 M de nodes en RAM.
#   python v9isles_no.py <ISO> [EPS_dp] [KEEP_frac] [min_km2] [BOX]
import sys, gzip, json, math, os, time
import numpy as np
from collections import defaultdict
from matplotlib.path import Path as MPath

ISO = sys.argv[1] if len(sys.argv) > 1 else 'NO'
EPS = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0005
KEEP = float(sys.argv[3]) if len(sys.argv) > 3 else 0.65
MIN_KM2 = float(sys.argv[4]) if len(sys.argv) > 4 else 5.0
BOX = None
if len(sys.argv) > 5 and sys.argv[5]:
    BOX = tuple(float(x) for x in sys.argv[5].split(','))
    if len(BOX) != 4: BOX = None

D = '/home/user/artifacts/v9/data/' + ISO + '/'
OUT = '/home/user/artifacts/v9/out/final/%s.json.gz' % ISO
BD = D + 'bin/'

wids = np.fromfile(BD + 'eways_ids.bin', dtype=np.int64)
woff = np.fromfile(BD + 'eways_off.bin', dtype=np.int64)
wrefs = np.fromfile(BD + 'eways_refs.bin', dtype=np.int64)
wcoast = np.fromfile(BD + 'eways_coast.bin', dtype=np.uint8)
# index interne i -> way id
wid_of = {int(wids[i]): i for i in range(len(wids))}

z = np.load(D + 'nodes.npz')
nids, nlons, nlats = z['ids'], z['lons'], z['lats']

def coords(arr):
    i = np.searchsorted(nids, arr)
    return nlons[i], nlats[i]

def rl_of(i):
    return wrefs[woff[i]:woff[i + 1]]

# ways de cote avec >= 3 refs (points extremes + 1)
cset = []
for i in range(len(wids)):
    if wcoast[i] != 1: continue
    if woff[i + 1] - woff[i] >= 3: cset.append(i)
print('ways de cote:', len(cset))

adj = defaultdict(list)
for i in cset:
    r = rl_of(i)
    a, b = int(r[0]), int(r[-1])
    if a == b and len(r) >= 4:
        pass  # way circulaire : un seul endpoint
    adj[a].append(i)
    if b != a: adj[b].append(i)

parent = {}
def find_(x):
    while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
    return x
def union_(a, b):
    ra, rb = find_(a), find_(b)
    if ra != rb: parent[ra] = rb
for i in cset: parent[i] = i
for nd in adj:
    lst = adj[nd]
    for x in lst[1:]:
        union_(lst[0], x)
comps = defaultdict(list)
for i in cset:
    comps[find_(i)].append(i)
print('composantes:', len(comps))

def pipv(poly_xy, PX, PY):
    a = np.asarray(poly_xy, dtype=float)
    x, y = a[:, 0], a[:, 1]
    x2, y2 = np.roll(x, -1), np.roll(y, -1)
    inside = np.zeros(PX.shape, dtype=bool)
    for i in range(len(x)):
        cond = (y[i] > PY) != (y2[i] > PY)
        with np.errstate(divide='ignore', invalid='ignore'):
            xint = (x2[i] - x[i]) * (PY - y[i]) / (y2[i] - y[i]) + x[i]
        inside ^= cond & (PX < xint)
    return inside

# --- exclusion du continent (ps[0] du bloc) ---
blk = None
with gzip.open(OUT) as f: blk = json.load(f)
_main = []
_s = blk['ps'][0].replace('Z', ' ').replace('M', ' ').replace('L', ' ').split()
_main = [(float(_s[k]), float(_s[k + 1])) for k in range(0, len(_s), 2)]
INV = lambda y: math.degrees(math.atan(math.sinh(math.radians(y))))
_mp = MPath([(p[0], INV(p[1])) for p in _main])
_lon0, _lon1 = min(p[0] for p in _main), max(p[0] for p in _main)
_lat0, _lat1 = min(INV(p[1]) for p in _main), max(INV(p[1]) for p in _main)
_gx = np.arange(_lon0, _lon1 + 0.05, 0.05)
_gy = np.arange(_lat0, _lat1 + 0.05, 0.05)
_GX, _GY = np.meshgrid(_gx, _gy)
_inside_main = _mp.contains_points(np.column_stack([_GX.ravel(), _GY.ravel()])).reshape(_GX.shape)
_MSX = _GX[_inside_main]; _MSY = _GY[_inside_main]
print('echantillons interieur continental:', len(_MSX))

def hierholzer(comp):
    ws = set(comp)
    deg = defaultdict(int)
    for i in comp:
        r = rl_of(i); deg[int(r[0])] += 1; deg[int(r[-1])] += 1
    odd = [n for n, d in deg.items() if d % 2 == 1]
    bridge = None; bnodes = None
    if len(odd) == 2:
        a, b = odd
        bridge = True; bnodes = (a, b)
        adj[a].append(-1); adj[b].append(-1)
    r0 = rl_of(comp[0])
    st = [int(r0[0])]; out = []
    while st:
        v = st[-1]
        nxt = None
        for w in adj[v]:
            if w == -1:
                if bridge is not None: nxt = -1; break
                continue
            if w in ws: nxt = w; break
        if nxt == -1:
            bridge = None
            st.append(bnodes[1] if st[-1] == bnodes[0] else bnodes[0])
        elif nxt is None:
            out.append(st.pop())
        else:
            ws.discard(nxt)
            r = rl_of(nxt)
            if int(r[0]) == v: st.append(int(r[-1]))
            else: st.append(int(r[0]))
    if len(odd) == 2:
        try: adj[odd[0]].remove(-1); adj[odd[1]].remove(-1)
        except ValueError: pass
    if len(out) < 4 or out[0] != out[-1]: return None
    return out

def cycle_coords(comp, cyc):
    # reinsere les refs interieurs de chaque way dans l'ordre du cycle
    pts = None
    for a, b in zip(cyc, cyc[1:]):
        found = False
        for w in adj[a]:
            if w == -1: continue
            r = rl_of(w)
            ra, rb = int(r[0]), int(r[-1])
            if ra == a and rb == b: sq = r
            elif rb == a and ra == b: sq = r[::-1]
            else: continue
            use = sq if pts is None else sq[1:]
            cc = np.column_stack(coords(use.copy()))
            pts = cc if pts is None else np.vstack([pts, cc])
            found = True; break
        if not found:
            if pts is None: return None
            cc = np.column_stack(coords(np.array([b], dtype=np.int64)))
            pts = np.vstack([pts, cc])
    return pts

def comp_pts(comp):
    # renvoie coords (N,2) d'une ile fermee, ou None
    if len(comp) == 1:
        r = rl_of(comp[0])
        if int(r[0]) == int(r[-1]) and len(r) >= 8:
            return np.column_stack(coords(r.copy()))
        return None
    if len(comp) == 2:
        r1, r2 = rl_of(comp[0]), rl_of(comp[1])
        if {int(r1[0]), int(r1[-1])} == {int(r2[0]), int(r2[-1])}:
            sq = r2 if int(r2[0]) == int(r1[-1]) else r2[::-1]
            both = np.concatenate([r1, sq[1:]])
            return np.column_stack(coords(both))
        return None
    # ouverte a 2 impairs -> walk_chain ferme par corde
    deg = defaultdict(int)
    for i in comp:
        r = rl_of(i); deg[int(r[0])] += 1; deg[int(r[-1])] += 1
    odd = [n for n, d in deg.items() if d % 2 == 1]
    if len(odd) == 2:
        cur = odd[0]; seen = set(); ids_seq = [cur]; wss = set(comp)
        while True:
            cand = [w for w in adj[cur] if w in wss and w not in seen and w != -1]
            if not cand: break
            w = cand[0]; seen.add(w)
            r = rl_of(w)
            seq = r if int(r[0]) == cur else r[::-1]
            ids_seq += [int(t) for t in seq[1:]]; cur = int(seq[-1])
        if cur == odd[1] and len(seen) == len(wss):
            arr = np.array(ids_seq + [ids_seq[0]], dtype=np.int64)
            return np.column_stack(coords(arr))
    cyc = hierholzer(comp)
    if cyc is None: return None
    return cycle_coords(comp, cyc)

def shoelace_km2(lonlat):
    a = np.asarray(lonlat, dtype=float)
    lat0 = math.radians((a[:, 1].max() + a[:, 1].min()) / 2)
    x = a[:, 0] * 111.32 * math.cos(lat0)
    y = a[:, 1] * 110.57
    return abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2

def dp_simplify(pts, eps):
    n = len(pts)
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

T0 = time.time()
kept = []
N = len(comps); done = 0
MONSTER = int(os.environ.get('MONSTER', '60000'))
monstres = 0
for comp in comps.values():
    done += 1
    if done % 2000 == 0:
        print('scan %d/%d %.0fs' % (done, N, time.time() - T0), flush=True)
    ll = comp_pts(comp)
    if ll is None or len(ll) < 8: continue
    lo0, lo1 = ll[:, 0].min(), ll[:, 0].max()
    la0, la1 = ll[:, 1].min(), ll[:, 1].max()
    if BOX:
        if (lo0 + lo1) / 2 < BOX[0] or (lo0 + lo1) / 2 > BOX[1] or (la0 + la1) / 2 < BOX[2] or (la0 + la1) / 2 > BOX[3]:
            continue
    # exclusion continent : echantillon de la grille continentale dans la bbox
    msk = (_MSX >= lo0) & (_MSX <= lo1) & (_MSY >= la0) & (_MSY <= la1)
    ii = np.nonzero(msk)[0]
    if len(ii) > 0:
        ii = ii[::max(1, len(ii) // 400)]
        if pipv(ll, _MSX[ii], _MSY[ii]).any(): continue
    km2 = shoelace_km2(ll)
    if km2 < MIN_KM2: continue
    if km2 > MONSTER:
        monstres += 1
        print('monstre rejete %.0f km2 (%d pts)' % (km2, len(ll)), flush=True)
        continue
    kept.append((km2, ll))
print('chaines closes gardees: %d, monstres: %d (%.0fs)' % (len(kept), monstres, time.time() - T0))

kept.sort(key=lambda t: -t[0])
nkeep = max(1, int(round(KEEP * len(kept))))
kept = kept[:nkeep]
print('iles gardees: %d / %d (aire %.0f km2)' % (len(kept), nkeep, sum(t[0] for t in kept)))

MY = lambda la: math.degrees(math.asinh(math.tan(math.radians(la))))
ps = []; tot = 0
for km2, ll in kept:
    m = np.column_stack([ll[:, 0], [MY(v) for v in ll[:, 1]]])
    m = dp_simplify(m, EPS)
    if len(m) < 4: continue
    d = ''
    for k, p in enumerate(m):
        d += ('M' if k == 0 else 'L') + str(round(float(p[0]), 5)) + ' ' + str(round(float(p[1]), 5))
        tot += 1
    ps.append(d + 'Z')

blk.setdefault('ps', []).extend(ps)
blk['boucles'] = len(blk['ps'])
blk['pts'] = blk.get('pts', 0) + tot
blk['iles'] = len(ps)
blk['methode'] = blk.get('methode', '') + '+iles'
with gzip.open(OUT, 'wb') as f:
    f.write(json.dumps(blk).encode())
print('bloc %s: +%d iles, +%d pts ; total boucles %d' % (ISO, len(ps), tot, blk['boucles']))
