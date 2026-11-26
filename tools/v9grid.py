#!/usr/bin/env python
# v9grid.py — silhouette terrestre d'un pays par rasteurisation.
#   python v9grid.py <ISO> [DX_deg] [BAND_deg]
# 1) masque admin : anneaux land9.json.gz rasteurisés (even-odd, scanlines numpy)
# 2) mer : cellules du masque situées côté EAU (droite) d'un segment coastline
#    (convention OSM : terre à gauche du way natural=coastline), dans une bande BAND
# 3) contours : suivi de sommets (pas de 1 cellule) -> Douglas-Peucker -> bloc
import sys, gzip, json, math, os
import numpy as np

ISO = sys.argv[1]
DX = float(sys.argv[2]) if len(sys.argv) > 2 else 0.001
BAND = float(sys.argv[3]) if len(sys.argv) > 3 else 0.18
D = '/home/user/artifacts/v9/data/' + ISO
OUT = '/home/user/artifacts/v9/out/final/%s.json.gz' % ISO
YC = 0.74  # correction d'aspect lat ~45°

NOMS_FR = {'AL':'Albanie','AT':'Autriche','BA':'Bosnie-Herzégovine','BE':'Belgique','BG':'Bulgarie',
'CH':'Suisse','CY':'Chypre','CZ':'Tchéquie','DK':'Danemark','EE':'Estonie','GR':'Grèce','HR':'Croatie',
'HU':'Hongrie','IE':'Irlande','IS':'Islande','LT':'Lituanie','LU':'Luxembourg','LV':'Lettonie',
'MD':'Moldavie','ME':'Monténégro','MK':'Macédoine du Nord','MT':'Malte','NL':'Pays-Bas','PL':'Pologne',
'PT':'Portugal','RO':'Roumanie','RS':'Serbie','SI':'Slovénie','SK':'Slovaquie','UA':'Ukraine','XK':'Kosovo'}

def jload(p):
    with gzip.open(p) as f: return json.load(f)

ways = jload(D + '/ways.json.gz')
nodes = jload(D + '/nodes.json.gz')
land9 = jload(D + '/land9.json.gz')
wm = {int(w['id']): w for w in ways}
nm = {}
for i in range(len(nodes['ids'])):
    nm[int(nodes['ids'][i])] = (nodes['lons'][i], nodes['lats'][i])

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
x0, x1 = min(xs) - 0.02, max(xs) + 0.02
y0, y1 = min(ys) - 0.02, max(ys) + 0.02
DY = DX / YC
NX = int((x1 - x0) / DX) + 1
NY = int((y1 - y0) / DY) + 1
print('grille %dx%d = %.1f Mcell, anneaux %d' % (NX, NY, NX*NY/1e6, len(rings)))
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
            lo = xi[k]; hi = xi[k+1]
            c0 = int(np.ceil((lo - x0) / DX - 0.5)); c1 = int(np.floor((hi - x0) / DX - 0.5))
            c0 = max(c0, 0); c1 = min(c1, NX - 1)
            if c1 >= c0: mask[row, c0:c1+1] = True
print('masque: %.2f%% cellules' % (100*mask.mean()))

def inside_mask(lon, lat):
    c = int((lon - x0) / DX); r = int((lat - y0) / DY)
    if 0 <= c < NX and 0 <= r < NY: return bool(mask[r, c])
    return False

coast_seg = []
nco = 0
def dp_simplify(pts, eps):
    # pts ndarray(n,2); renvoie ndarray reduit
    n = len(pts)
    if n < 3: return pts
    keep = np.zeros(n, dtype=bool); keep[0] = keep[-1] = True
    stk = [(0, n - 1)]
    while stk:
        a, b = stk.pop()
        if b <= a + 1: continue
        pa, pb = pts[a], pts[b]
        m = pts[a+1:b]
        e = pb - pa
        L2v = e[0]*e[0] + e[1]*e[1]
        if L2v == 0: dist = np.hypot(*(m - pa).T)
        else:
            t = np.clip(((m - pa) @ e) / L2v, 0, 1)
            proj = pa + t[:,None]*e
            dist = np.hypot(*(m - proj).T)
        k = int(np.argmax(dist))
        if dist[k] > eps:
            kk = a + 1 + k
            keep[kk] = True
            stk.append((a, kk)); stk.append((kk, b))
    return pts[keep]
for w in ways:
    tg = w.get('tags') or {}
    if tg.get('natural') != 'coastline': continue
    refs = w['refs']
    c = nm.get(refs[len(refs)//2])
    if not c or not inside_mask(*c): continue
    nco += 1
    P = np.array([nm[r] for r in refs if r in nm])
    P = dp_simplify(P, 0.3 * DX)
    for i in range(len(P) - 1):
        A, Bv = P[i], P[i+1]
        coast_seg.append((A[0], A[1], Bv[0], Bv[1]))
print('littoral: ways %d, segments %d' % (nco, len(coast_seg)))

sea = np.zeros((NY, NX), dtype=bool)
for cx0, cy0, cx1, cy1 in coast_seg:
    dxl = (cx1 - cx0) * YC; dyl = (cy1 - cy0)
    L2 = dxl*dxl + dyl*dyl or 1e-24
    i_lo = max(0, int((min(cx0, cx1) - BAND - x0) / DX)); i_hi = min(NX - 1, int((max(cx0, cx1) + BAND - x0) / DX))
    j_lo = max(0, int((min(cy0, cy1) - BAND - y0) / DY)); j_hi = min(NY - 1, int((max(cy0, cy1) + BAND - y0) / DY))
    if i_hi < i_lo or j_hi < j_lo: continue
    ii = (x0 + (np.arange(i_lo, i_hi + 1) + 0.5) * DX - cx0) * YC
    jj = (y0 + (np.arange(j_lo, j_hi + 1) + 0.5) * DY - cy0)
    PX = np.broadcast_to(ii[None, :], (len(jj), len(ii)))
    PY = np.broadcast_to(jj[:, None], (len(jj), len(ii)))
    t = (PX * dxl + PY * dyl)
    dperp = (PX * dyl - PY * dxl)
    LL = math.sqrt(L2)
    # dperp = dist_perp * LL ; dperp > 0 = a GAUCHE du way = TERRE (convention OSM)
    sel = (t >= 0) & (t <= LL) & (dperp < 0) & (dperp > -BAND * YC * LL)
    sea[j_lo:j_hi+1, i_lo:i_hi+1] |= sel
sea &= mask
land = mask & ~sea
km2 = land.sum() * DX * 111.32 * math.cos(math.radians((y0+y1)/2)) * DY * 111.13
print('mer: %.2f%% cellules; terre ~%.0f km2' % (100*sea.mean(), km2))

# ---- contours via matplotlib (marching squares, lignes de niveau 0.5) ----
import os as _os
if _os.environ.get('V9PROBE'):
    PROBES = [(15.97,45.81,'Zagreb'),(16.44,43.51,'Split'),(16.19,43.16,'Hvar'),(14.4,44.97,'Cres'),
              (18.09,42.65,'Dubrovnik'),(18.69,45.51,"Osijek"),(17.15,45.09,"BIH-Sabac"),(16.0,44.0,'mer Adriatique'),
              (15.6,45.1,'ZagrebW'),(16.5,45.8,'Drava'),(13.5,45.5,'Istrie N')]
    for px, py, name in PROBES:
        r = int((py - y0) / DY); c = int((px - x0) / DX)
        print('PROBE %-14s mask=%s sea=%s land=%s' % (name, mask[r, c], sea[r, c], land[r, c]))
import matplotlib
matplotlib.use('Agg')
import os as _os
if _os.environ.get('V9PROBE'):
    PROBES = [(15.97,45.81,'Zagreb'),(16.44,43.51,'Split'),(16.19,43.16,'Hvar'),(14.4,44.97,'Cres'),
              (18.09,42.65,'Dubrovnik'),(18.69,45.51,"Osijek"),(17.15,45.09,"BIH-Sabac"),(16.0,44.0,'mer Adriatique'),
              (15.6,45.1,'ZagrebW'),(16.5,45.8,'Drava'),(13.5,45.5,'Istrie N')]
    for px, py, name in PROBES:
        r = int((py - y0) / DY); c = int((px - x0) / DX)
        print('PROBE %-14s mask=%s sea=%s land=%s' % (name, mask[r, c], sea[r, c], land[r, c]))
import matplotlib.pyplot as plt
f0 = land.astype(float).T  # (NX, NY): x=cols
xc = x0 + (np.arange(NX) + 0.5) * DX
yc = y0 + (np.arange(NY) + 0.5) * DY
cs = plt.contour(xc, yc, f0.T, levels=[0.5])
segs = []
for path in cs.get_paths():
    V = np.asarray(path.vertices); C = path.codes
    if C is None:
        segs.append(V); continue
    starts = np.nonzero(C == 1)[0]
    ends = np.append(starts[1:], len(V))
    for a, b in zip(starts, ends):
        seg = V[a:b]
        if len(seg) > 6: segs.append(seg)
plt.close()
print('segments contour:', len(segs))
rings_v = [s for s in segs if len(s) > 6]
print('anneaux:', len(rings_v))
# DP sur les points du contour (lon/lat -> merc approx)
EPS = 0.35 * DX
MY = lambda la: math.degrees(math.asinh(math.tan(math.radians(la))))
rings_m = []
for seg in rings_v:
    m = np.stack([seg[:,0], np.array([MY(l) for l in seg[:,1]])], axis=1)
    m = dp_simplify(m, EPS * 1.4)
    if len(m) >= 4: rings_m.append(m)
print('anneaux merc apres DP:', len(rings_m))

ps = []
tot = 0
gx0, gy0, gx1, gy1 = 1e9, 1e9, -1e9, -1e9
for m in rings_m:
    d = ''
    for k, p in enumerate(m):
        X = round(float(p[0]), 5); Y = round(float(p[1]), 5)
        d += ('M' if k == 0 else 'L') + str(X) + ' ' + str(Y)
        tot += 1
        gx0 = min(gx0, X); gx1 = max(gx1, X); gy0 = min(gy0, Y); gy1 = max(gy1, Y)
    ps.append(d + 'Z')
print('ps:', len(ps), 'points', tot)

# ---- bloc final : garde ext de l ancien bloc, remplace ps ----
blk = {'iso': ISO, 'nom': NOMS_FR.get(ISO, ISO), 'ps': ps, 'b': [gx0, gy0, gx1, gy1],
       'boucles': len(ps), 'pts': tot, 'methode': 'grid%.0fm' % (DX * 111000)}
if os.path.exists(OUT):
    try:
        old = jload(OUT)
        for k in ('ext', 'nmiss', 'anneaux'):
            if k in old: blk[k] = old[k]
        blk['nom_voie'] = old.get('nom')
    except Exception as e:
        print('ancien bloc illisible:', e)
with gzip.open(OUT, 'wb') as f:
    f.write(json.dumps(blk).encode())
print('bloc ecrit:', OUT, 'boucles', len(ps))