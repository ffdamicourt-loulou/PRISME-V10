#!/usr/bin/env python
# v9land.py — silhouette TERRESTRE d'un pays côtier : admin ∖ mer.
#   python v9land.py <ISO> [DX_deg] [ISO3]
# Principes (remplace la version « bande » trop grossière de v9grid.py) :
#   1. masque admin = anneaux land9.json.gz rastérisés en even-odd (scanlines)
#   2. murs = cellules traversées par les ways natural=coastline (déjà dans le
#      package ; HR/GR : téléchargés par extract.js via tags)
#   3. graines d'eau = cellules du CÔTÉ MER d'un segment de côte (convention
#      OSM terre à gauche), puis inondation (binary_propagation) DANS le masque
#      → toute l'eau territoriale est atteinte, les terres (continents protégés
#      par les côtes, îles) restent : la silhouette a le vrai littoral OSM,
#      jusqu'aux plus petites îles.
#   4. contour (marching squares) + Douglas-Peucker → bloc final.
import sys, gzip, json, math, os
import numpy as np
from scipy import ndimage

ISO = sys.argv[1] if len(sys.argv) > 1 else 'HR'
DX = float(sys.argv[2]) if len(sys.argv) > 2 else 0.001      # degrés lon (~110 m)
EPS = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5 * DX   # tolerance DP
D = '/home/user/artifacts/v9/data/' + ISO
OUT = '/home/user/artifacts/v9/out/final/%s.json.gz' % ISO
YC = 0.74  # correction d'aspect lat ~45°

def jload(p):
    with gzip.open(p) as f: return json.load(f)

ways = jload(D + '/ways.json.gz')
nodes = jload(D + '/nodes.json.gz')
land9 = jload(D + '/land9.json.gz')
wm = {int(w['id']): w for w in ways}
_ids = np.asarray(nodes['ids'], dtype=np.int64)
_ord = np.argsort(_ids)
_ids = _ids[_ord]
_lons = np.asarray(nodes['lons'], dtype=np.float64)[_ord]
_lats = np.asarray(nodes['lats'], dtype=np.float64)[_ord]
class _NodeMap:
    def _pos(self, k):
        i = np.searchsorted(_ids, k)
        return i if i < len(_ids) and _ids[i] == k else -1
    def get(self, k, d=None):
        i = self._pos(k)
        return d if i < 0 else (float(_lons[i]), float(_lats[i]))
    def __contains__(self, k):
        return self._pos(k) >= 0
    def __getitem__(self, k):
        i = self._pos(k)
        if i < 0: raise KeyError(k)
        return (float(_lons[i]), float(_lats[i]))
    def bulk(self, refs):
        # renvoie tableau (n,2) des refs connues, dans l'ordre
        r = np.asarray(refs, dtype=np.int64)
        i = np.searchsorted(_ids, r)
        ok = (i < len(_ids)) & (_ids[np.minimum(i, len(_ids)-1)] == r)
        i2 = i[ok]
        return np.column_stack([_lons[i2], _lats[i2]])
nm = _NodeMap()

# ---- 1. masque admin (anneaux remplis even-odd) ----
rings = []
for ring in land9['rings']:
    pts = []
    for wid, rev in ring:
        w = wm.get(int(wid))
        if not w: continue
        refs = w['refs'][::-1] if rev else w['refs']
        for r in refs:
            c = nm.get(r)
            if c: pts.append(c)
    if len(pts) > 4: rings.append(pts)
xs = [p[0] for rg in rings for p in rg]; ys = [p[1] for rg in rings for p in rg]
PAD = 0.05
x0, x1 = min(xs) - PAD, max(xs) + PAD
y0, y1 = min(ys) - PAD, max(ys) + PAD
# BOX (env) : limiter la grille (ex NO sans Svalbard, franges hors-Europe)
if os.environ.get('BOX', '').strip():
    bx0, bx1, by0, by1 = [float(v) for v in os.environ['BOX'].split(',')]
    x0, x1 = max(x0, bx0), min(x1, bx1)
    y0, y1 = max(y0, by0), min(y1, by1)
    print('BOX appliquee: lon[%.1f,%.1f] lat[%.1f,%.1f]' % (x0, x1, y0, y1))
DY = DX / YC
NX = int((x1 - x0) / DX) + 1
NY = int((y1 - y0) / DY) + 1
print('grille %dx%d = %.1f Mcell, anneaux %d' % (NX, NY, NX * NY / 1e6, len(rings)))
mask = np.zeros((NY, NX), dtype=bool)
for rg in rings:
    ax = np.array([p[0] for p in rg]); ay = np.array([p[1] for p in rg])
    bx = np.roll(ax, -1); by = np.roll(ay, -1)
    rr0 = max(0, int((max(ay.min(), by.min()) - y0) / DY) - 1)
    rr1 = min(NY - 1, int((max(ay.max(), by.max()) - y0) / DY) + 1)
    for row in range(rr0, rr1 + 1):
        yy = y0 + (row + 0.5) * DY
        sel = ((ay <= yy) & (by > yy)) | ((by <= yy) & (ay > yy))
        if not sel.any(): continue
        xa = ax[sel]; xb = bx[sel]; ya = ay[sel]; yb = by[sel]
        xi = xa + (yy - ya) * (xb - xa) / (yb - ya)
        xi.sort()
        for k in range(0, len(xi) - 1, 2):
            lo = xi[k]; hi = xi[k + 1]
            c0 = int(np.ceil((lo - x0) / DX - 0.5)); c1 = int(np.floor((hi - x0) / DX - 0.5))
            c0 = max(c0, 0); c1 = min(c1, NX - 1)
            if c1 >= c0: mask[row, c0:c1 + 1] = True
print('masque: %.2f%% cellules' % (100 * mask.mean()))

# ---- 2+3. murs côtiers + graines côté mer ----
wall = np.zeros((NY, NX), dtype=bool)
seed = np.zeros((NY, NX), dtype=bool)
nco = 0
W = float(os.environ.get('W9', 4.0)) * DX  # demi-largeur du balayage perpendiculaire
_MINW = int(os.environ.get('MINW', '0'))
for w in ways:
    tg = w.get('tags') or {}
    if tg.get('natural') != 'coastline': continue
    refs = w['refs']
    if len(refs) < _MINW: continue
    P = nm.bulk(refs)
    if len(P) < 2: continue
    # cible : seulement ce qui touche (en gros) le masque
    if not (P[:,0].min() - 0.3 < x1 and P[:,0].max() + 0.3 > x0): continue
    nco += 1
    for i in range(len(P) - 1):
        A, B = P[i], P[i + 1]
        dxl = (B[0] - A[0]); dyl = (B[1] - A[1])
        L2v = dxl * dxl + dyl * dyl
        if L2v < 1e-18: continue
        LL = np.sqrt((dxl ** 2) * YC ** 2 + dyl ** 2)
        Ldeg = np.sqrt(L2v)
        i_lo = max(0, int((min(A[0], B[0]) - W - x0) / DX)); i_hi = min(NX - 1, int((max(A[0], B[0]) + W - x0) / DX))
        j_lo = max(0, int((min(A[1], B[1]) - W - y0) / DY)); j_hi = min(NY - 1, int((max(A[1], B[1]) + W - y0) / DY))
        if i_hi < i_lo or j_hi < j_lo: continue
        ii = x0 + (np.arange(i_lo, i_hi + 1) + 0.5) * DX - A[0]
        jj = y0 + (np.arange(j_lo, j_hi + 1) + 0.5) * DY - A[1]
        PX = np.broadcast_to(ii[None, :], (len(jj), len(ii)))
        PY = np.broadcast_to(jj[:, None], (len(jj), len(ii)))
        t = (PX * dxl + PY * dyl)   # longueur du segment en degres (approx)
        # TERRE A GAUCHE du way (convention OSM) :
        #   cross = dxl*PY - dyl*PX > 0  (anisotropie: lon rescalee par YC plus bas)
        LEFTP = (dxl * PY - dyl * PX) * YC   # facteur YC commun -> signe inchange
        inseg = (t >= -0.6 * Ldeg) & (t <= 1.6 * Ldeg) & (np.abs(LEFTP) <= W * LL)
        near = inseg & (np.abs(LEFTP) <= float(os.environ.get('WALLN', 2.0)) * DX * LL)
        wall[j_lo:j_hi + 1, i_lo:i_hi + 1] |= near
print('littoral: %d ways' % nco, flush=True)
import time as _tm
_T0GLOB=_tm.time()
print('T murs: %.0fs' % (_tm.time()-_T0GLOB), flush=True)

# ---- boucher les extremites libres de la chaine de cote (frontalieres) :
#      a chaque node "dangling" (bout de chaine de coast ways), la mer
#      contournerait le bout du mur et inonderait tout l'interieur du pays.
#      On prolonge un mur obstruant en ligne droite jusqu'a la premiere
#      cellule HORS du masque (frontiere terrestre voisine), ce qui ferme la
#      boucle continent-mur-mer de mananche etanche. ----
from collections import defaultdict
_deg = defaultdict(int)
for w in ways:
    if (w.get('tags') or {}).get('natural') != 'coastline': continue
    for e in (w['refs'][0], w['refs'][-1]): _deg[e] += 1
# index des extremites connues (premier/dernier node present dans nm) par way :
# evite un scan O(dangling x nways) devastateur sur les archipels
_lastK = {}; _firstK = {}
for w in ways:
    if (w.get('tags') or {}).get('natural') != 'coastline': continue
    _r = np.asarray(w['refs'], dtype=np.int64)
    if len(_r) < 2: continue
    _ii = np.minimum(np.searchsorted(_ids, _r), len(_ids) - 1)
    _kn = np.nonzero(_ids[_ii] == _r)[0]
    if len(_kn) < 2: continue
    _firstK.setdefault(int(_r[_kn[0]]), (int(_r[_kn[0]]), int(_r[_kn[1]])))
    _lastK.setdefault(int(_r[_kn[-1]]), (int(_r[_kn[-2]]), int(_r[_kn[-1]])))
nplug = 0
for _n, _d in _deg.items():
    if _d != 1 or _n not in nm: continue
    lon, lat = nm[_n]
    # bouchon frontalier : prolonger le mur au-dela du node pendant,
    # dans le prolongement du dernier segment de cote (0.2 deg), pour couper
    # la bande cotiere entre la fin du trait de cote et la frontiere.
    lastW = _lastK.get(_n) or _firstK.get(_n)
    if lastW is None: continue
    U = np.array(nm[lastW[0]]); P = np.array(nm[lastW[1]])
    d = P - U
    nrm = np.hypot(d[0], d[1])
    if nrm < 1e-9: continue
    d = d / nrm
    Q = P + d * 0.2
    # rasteriser P->Q (et 2 cellules d'epaisseur)
    steps = int(0.2 / min(DX, DY)) * 2 + 1
    rrays = np.round((P[1] + (Q[1] - P[1]) * np.linspace(0, 1, steps) - y0) / DY).astype(int)
    crays = np.round((P[0] + (Q[0] - P[0]) * np.linspace(0, 1, steps) - x0) / DX).astype(int)
    ok = (rrays >= 0) & (rrays < NY) & (crays >= 0) & (crays < NX)
    rrays = rrays[ok]; crays = crays[ok]
    if len(rrays) == 0: continue
    for dr in range(-1, 2):
        for dc in range(-1, 2):
            wall[np.clip(rrays + dr, 0, NY - 1), np.clip(crays + dc, 0, NX - 1)] = True
    nplug += 1
    print('  bouchon rayon: node %s (%.4f,%.4f) dir (%.3f,%.3f)' % (_n, P[0], P[1], d[0], d[1]))
print('bouchons frontaliers: %d' % nplug)

# sceller les portes (bouches d'estuaire petites brèches du trait de cote) :
# fermeture morphologique du mur, les detroits larges (>= ~10 cellules/1 km)
# restent ouverts
wall = ndimage.binary_closing(wall, structure=np.ones((int(os.environ.get("CLOS", 3)),) * 2 + (0,) + (0,), dtype=bool) if False else np.ones((int(os.environ.get("CLOS", 3)), int(os.environ.get("CLOS", 3))), dtype=bool))
# interdire encore le passage diagonal : dilatation 4-conn du mur (les paires
# de cellules de mur ne se touchant que par un coin deviennent un bouchon plein)
wall = ndimage.binary_dilation(wall, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=bool))

# ---- graines : HAUTE MER (points designes, l'orientation des ways OSM n'est
#      pas fiable : des ways de cote a l'envers placaient des graines sur la
#      terre -> inondation du continent). Les murs (trait de cote OSM) restent
#      l'unique obstacle : la mer atteint toutes les baies, la terre et les
#      iles protegees par le trait de cote restent intactes. ----
SEAS = {
    'HR': '14.2,44.9',
    'GR': '20.2,38.1;24.9,37.2;24.5,35.3',
}
if len(sys.argv) > 4 and sys.argv[4].strip():
    SEAS[ISO] = sys.argv[4]
# garde-fou : kd-tree des nodes du trait de cote -> une graine doit etre a
# >4 km de toute cote ET dans le masque (empeche une graine posee sur une ile)
from scipy.spatial import cKDTree
_cnL = []
for w in ways:
    if (w.get('tags') or {}).get('natural') != 'coastline': continue
    A = nm.bulk(w['refs'])
    if len(A): _cnL.append(A)
_cn = np.vstack(_cnL) if _cnL else None
if _cn is not None and len(_cn) > 2_000_000:
    _cn = _cn[:: len(_cn) // 2_000_000]
    print('kd-tree sous-echantillonne: %d pts' % len(_cn), flush=True)
_kd = None if os.environ.get('SKIPKD') else (cKDTree(_cn) if _cn is not None else None)
if _kd is None: print('kd-tree: SKIP (graines fournies/villes)')
seed = np.zeros((NY, NX), dtype=bool)
for pair in SEAS.get(ISO, '').split(';'):
    pair = pair.strip()
    if not pair: continue
    if _kd is not None and _kd.query(np.array([[float(pair.split(',')[0]), float(pair.split(',')[1])]]))[0][0] < 0.004:
        print('  graine rejetee (trop proche de la cote): %s' % pair); continue
    lo, la = [float(v) for v in pair.split(',')]
    c = int((lo - x0) / DX); r = int((la - y0) / DY)
    if 0 <= c < NX and 0 <= r < NY and mask[r, c]:
        r0 = max(0, r - 3); r1 = min(NY - 1, r + 3)
        c0 = max(0, c - 3); c1 = min(NX - 1, c + 3)
        seed[r0:r1 + 1, c0:c1 + 1] = True
print('graines haute mer: %d cellules' % int(seed.sum()))
if not seed.any():
    # fallback : bande de 0.5 cellule au-dela du mur, cote... aucun tag fiable
    # -> on refuse plutot que d'inonder la terre
    print('ERREUR: aucun point de haute mer dans le masque pour', ISO)
    sys.exit(1)

print('T bouchons: %.0fs' % (_tm.time()-_T0GLOB), flush=True)
import gc as _gc
try:
    del ways, wm, nodes
except NameError: pass
try:
    del _cn, _cnL, _kd
except NameError: pass
_gc.collect()
print('memoire data liberee avant flood', flush=True)
seed &= mask & ~wall
_tf=_tm.time()
water = ndimage.binary_propagation(seed, mask=(mask & ~wall), structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=bool))
print('T flood: %.0fs' % (_tm.time()-_tf), flush=True)
# MODE LANDSEED : la graine est sur la TERRE (capitale/fond du pays) ; le flood
# propage = le compartiment terrestre, bloque par les murs de cote. Immune aux
# fuites par les tetes d'estuaire (le flood ne traverse pas le trait de cote).
_LSM = bool(os.environ.get('LANDSEED', '').strip())
# poches d'eau non atteintes : composantes du masque non-inondees dont toutes
# les cellules sont a <=4 cellules d'un mur -> c'est un chenal etroit -> EAU
if _LSM:
    floodland = water & mask
    # passe 2 : mer depuis des graines haute mer DANS le complement. Le
    # floodland forme une barriere : pas de fuite possible vers l'interieur.
    sea2 = os.environ.get('SEA2', '').strip()
    if sea2:
        comp = mask & ~wall & ~floodland
        sd2 = np.zeros((NY, NX), dtype=bool)
        for pair in sea2.split(';'):
            pair = pair.strip()
            if not pair: continue
            lo2, la2 = [float(v) for v in pair.split(',')]
            c = int((lo2 - x0) / DX); r = int((la2 - y0) / DY)
            if not (0 <= c < NX and 0 <= r < NY):
                print('  seed hors grille: %s' % pair); continue
            _ch = comp[max(0,r-3):r+4, max(0,c-3):c+4]
            if _ch.any():
                sd2[max(0, r - 3):r + 4, max(0, c - 3):c + 4] = True
            else:
                print('  seed reject comp: %s -> mask=%s wall=%s flood=%s' % (pair, bool(mask[r,c]), bool(wall[r,c]), bool(floodland[r,c])))
        print('graines mer passe-2: %d cellules' % int(sd2.sum()))
        w2 = ndimage.binary_propagation(sd2, mask=comp, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=bool))
        water = w2
    else:
        water = mask & ~floodland
    land = mask & ~water
    print('MODE LANDSEED: terre = %.2f%% du masque (%.0f km2 est.) ; eau = %.2f%%' % (
        100 * land.sum() / max(mask.sum(), 1),
        land.sum() * DX * 111.32 * math.cos(math.radians((y0 + y1) / 2)) * (DX / YC) * 111.13,
        100 * (water & mask).sum() / max(mask.sum(), 1)))
    n = 0
    print('MODE LANDSEED: terre = %.2f%% du masque (%.0f km2 est.)' % (
        100 * land.sum() / max(mask.sum(), 1),
        land.sum() * DX * 111.32 * math.cos(math.radians((y0 + y1) / 2)) * (DX / YC) * 111.13))
elif os.environ.get('CHANELS', '1') != '0':
  Wd = ndimage.distance_transform_edt(~wall)
  unflooded = mask & ~wall & ~water
  lab, n = ndimage.label(unflooded)
else:
  n = 0
if n:
    mx = ndimage.maximum(Wd, lab, index=np.arange(1, n + 1))
    mx = np.array([0] + list(mx))
    thin = (mx[lab] <= 4) & unflooded
    water = water | thin
    print('chanels reclasses en eau: %d cellules' % int(thin.sum()))

# iles : chaines de cote FERMEES -> polygones -> TERRE
# (une ile a une fuite d'inondation doit rester terre ; ses cotes forment une
#  chaine fermee de ways natural=coastline partages par node)
def chains_coast():
    byEnd = {}
    coastWays = [w for w in ways if (w.get('tags') or {}).get('natural') == 'coastline']
    cw = {}
    for w in coastWays:
        refs = [r for r in w['refs'] if r in nm]
        if len(refs) < 2: continue
        cw[w['id']] = refs
    for wid, refs in cw.items():
        for e in (refs[0], refs[-1]):
            byEnd.setdefault(e, []).append(wid)
    used = set(); rings = []
    for wid, refs in cw.items():
        if wid in used: continue
        used.add(wid)
        chain = [wid]; cur = refs[-1]
        while True:
            nxt = [x for x in byEnd.get(cur, []) if x not in used]
            if not nxt: break
            # choix deterministe : le way qui prolonge le mieux
            nw = cw[nxt[0]]
            chain.append(nxt[0]); used.add(nxt[0])
            if nw[0] == cur: cur = nw[-1]
            else: cur = nw[0]
        rr = []
        for cwid in chain:
            refs = cw[cwid]
            rr += refs if refs[0] == None else refs
        # ferme ?
        if rr[0] == rr[-1] and len(rr) > 8:
            rings.append(rr)
    return rings

isles = [] if (os.environ.get('ISLES','1')=='0' or _LSM) else chains_coast()
print('chaines de cote fermees:', len(isles))
nfix = 0
for rr in isles:
    if len(rr) > 4000: continue  # trop grande: risque de repeindre des golfes
    pts = nm.bulk(rr)
    if pts[:,0].max() - pts[:,0].min() > 0.5 or pts[:,1].max() - pts[:,1].min() > 0.35: continue
    if pts[:,0].min() < x0 or pts[:,0].max() > x1 or pts[:,1].min() < y0 or pts[:,1].max() > y1: continue
    # remplir (scanline dans la boite locale)
    ax=pts[:,0]; ay=pts[:,1]; bx=np.roll(ax,-1); by=np.roll(ay,-1)
    r0=max(0,int((ay.min()-y0)/DY)-1); r1=min(NY-1,int((ay.max()-y0)/DY)+1)
    c0=max(0,int((ax.min()-x0)/DX)-1); c1=min(NX-1,int((ax.max()-x0)/DX)+1)
    sub=np.zeros((r1-r0+1,c1-c0+1),dtype=bool)
    for row in range(r1-r0+1):
        yy=y0+(r0+row+0.5)*DY
        sel=((ay<=yy)&(by>yy))|((by<=yy)&(ay>yy))
        if not sel.any(): continue
        xa=ax[sel];xb=bx[sel];ya=ay[sel];yb=by[sel]
        xi=xa+(yy-ya)*(xb-xa)/(yb-ya)
        xi.sort()
        for k in range(0,len(xi)-1,2):
            a0=int(np.ceil((xi[k]-x0)/DX-0.5))-c0; a1=int(np.floor((xi[k+1]-x0)/DX-0.5))-c0
            a0=max(a0,0); a1=min(a1,sub.shape[1]-1)
            if a1>=a0: sub[row,a0:a1+1]=True
    reg=sub & mask[r0:r1+1,c0:c1+1]
    water[r0:r1+1,c0:c1+1] &= ~reg
    nfix+=int(reg.sum())
print('iles restaurees: %d cellules' % nfix)
if not _LSM:
    land = mask & ~water
if os.environ.get('MAINCOMP', '0') == '1' and not _LSM:
    MAIN = {'GR': (23.729, 37.984), 'HR': (15.97, 45.81)}
    if ISO in MAIN:
        lo, la = MAIN[ISO]
        _r = int((la - y0) / DY); _c = int((lo - x0) / DX)
        _sd = np.zeros((NY, NX), dtype=bool)
        _sd[max(0, _r - 2):_r + 3, max(0, _c - 2):_c + 3] = True
        _mn = ndimage.binary_propagation(_sd & land, mask=land, structure=np.ones((3, 3), dtype=bool))
        print('composante continentale: %d cellules (retirees %d)' % (int(_mn.sum()), int(land.sum() - _mn.sum())))
        land = _mn
import gc
for _v in ('seed', 'Wd', 'unflooded', 'lab', 'thin', 'wall'):
    if _v in dir(): pass
try: del seed, Wd, unflooded, lab, thin, wall
except Exception: pass
gc.collect()
km2 = land.sum() * DX * 111.32 * math.cos(math.radians((y0 + y1) / 2)) * (DX / YC) * 111.13
print('eau: %.2f%% du masque ; terre ~%.0f km²' % (100 * (water & mask).sum() / max(mask.sum(), 1), km2))

print('T jusqu aux contours: %.0fs' % (_tm.time()-_T0GLOB), flush=True)
# ---- 4. contours : marching squares maison (faible memoire) ----
# aretes dirigees, terre a GAUCHE ; id coin = r*(NX+1)+c
L = land.astype(np.uint8)
NC = (NY + 1, NX + 1)
starts = []   # id depart
ends = []     # id arrivee
dv = L[:, :-1] != L[:, 1:]           # cell (r,c) vs (r,c+1) -> arete verticale x=c+1, y in [r,r+1]
rr, cc = np.nonzero(dv)
landW = (L[np.nonzero(L[:, :-1])] if False else None)
lw = L[rr, cc]
# terre a l'ouest -> NORD : (r+1,c+1)->(r,c+1) ; terre a l'est -> SUD : (r,c+1)->(r+1,c+1)
starts.extend(((rr + 1) * NC[1] + cc + 1)[lw == 1].tolist())
ends.extend((rr * NC[1] + cc + 1)[lw == 1].tolist())
starts.extend((rr * NC[1] + cc + 1)[lw == 0].tolist())
ends.extend(((rr + 1) * NC[1] + cc + 1)[lw == 0].tolist())
dh = L[:-1, :] != L[1:, :]           # cell (r,c) vs (r+1,c) -> arete horizontale y=r+1, x in [c,c+1]
rr, cc = np.nonzero(dh)
ln = L[rr, cc]
# terre au nord -> EST : (r+1,c)->(r+1,c+1) ; terre au sud -> OUEST : (r+1,c+1)->(r+1,c)
starts.extend(((rr + 1) * NC[1] + cc)[ln == 1].tolist())
ends.extend(((rr + 1) * NC[1] + cc + 1)[ln == 1].tolist())
starts.extend(((rr + 1) * NC[1] + cc + 1)[ln == 0].tolist())
ends.extend(((rr + 1) * NC[1] + cc)[ln == 0].tolist())
nE = len(starts)
from collections import defaultdict
_byStart = defaultdict(list)
for k in range(nE):
    _byStart[starts[k]].append(k)
used = np.zeros(nE, dtype=bool)
segs = []
for k0 in range(nE):
    if used[k0]: continue
    used[k0] = True
    loop = [starts[k0], ends[k0]]
    cur = ends[k0]
    while cur != loop[0]:
        nxts = [e for e in _byStart.get(cur, ()) if not used[e]]
        if not nxts: break
        e = nxts[0]
        used[e] = True
        loop.append(ends[e])
        cur = ends[e]
    if len(loop) > 6 and loop[0] == loop[-1]:
        aid = np.array(loop)
        segs.append(np.stack([(aid % NC[1]) * DX + x0, (aid // NC[1]) * DY + y0], axis=1))
print('anneaux bruts:', len(segs))

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

MY = lambda la: math.degrees(math.asinh(math.tan(math.radians(la))))
ps = []; tot = 0
bx = [1e9, 1e9, -1e9, -1e9]
for seg in segs:
    m = np.stack([seg[:, 0], np.array([MY(l) for l in seg[:, 1]])], axis=1)
    m = dp_simplify(m, EPS)
    if len(m) < 4: continue
    d = ''
    for k, p in enumerate(m):
        X = round(float(p[0]), 5); Y = round(float(p[1]), 5)
        d += ('M' if k == 0 else 'L') + str(X) + ' ' + str(Y)
        tot += 1
        bx[0] = min(bx[0], X); bx[1] = min(bx[1], Y); bx[2] = max(bx[2], X); bx[3] = max(bx[3], Y)
    ps.append(d + 'Z')
print('boucles:', len(ps), 'points:', tot)

blk = {'iso': ISO, 'ps': ps, 'b': bx, 'boucles': len(ps), 'pts': tot,
       'methode': 'land:%.0fm' % (DX * 111000)}
if os.path.exists(OUT):
    try:
        old = jload(OUT)
        for k in old:
            if k not in blk and k != 'ps': blk[k] = old[k]
        blk['nom_voie'] = old.get('nom')
    except Exception as e:
        print('ancien bloc illisible:', e)
with gzip.open(OUT, 'wb') as f:
    f.write(json.dumps(blk).encode())
print('bloc écrit:', OUT)