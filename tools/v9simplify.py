#!/usr/bin/env python3
# v9simplify.py — simplifie les contours d'un bloc (Douglas-Peucker) pour
# atteindre une fraction cible des points.   python v9simplify.py <ISO> <fraction>
import sys, gzip, json, math, numpy as np

ISO = sys.argv[1]
FRAC = float(sys.argv[2])          # ex 0.70 = garder 70% des points
OUT = '/home/user/artifacts/v9/out/final/%s.json.gz' % ISO

def parse(p):
    t = [q for q in p.rstrip('Z').replace('M', 'L').split('L') if q]
    return np.array([[float(x) for x in q.split()] for q in t])

def dp_ring(pts, eps):
    # anneau FERME (pts[0]==pts[-1]) : 2 ancres = pts[0] et le point le plus
    # eloigne, puis DP sur chacune des 2 chaines, re-assemblage et re-fermeture.
    n = len(pts)
    if n < 6: return pts
    openp = pts[:-1]
    m = len(openp)
    k = int(np.argmax(np.hypot(openp[:, 0] - openp[0, 0], openp[:, 1] - openp[0, 1]))) 
    half1 = dp(openp[:k + 1], eps)
    half2 = dp(np.vstack([openp[k:], openp[0]]), eps)
    return np.vstack([half1[:-1], half2[:-1], openp[0]])

def dp(pts, eps):
    # Douglas-Peucker iteratif (pile)
    n = len(pts)
    if n < 5: return pts
    keep = np.zeros(n, dtype=bool); keep[0] = keep[-1] = True
    stk = [(0, n - 1)]
    while stk:
        a, b = stk.pop()
        if b - a < 2: continue
        segx = pts[b, 0] - pts[a, 0]; segy = pts[b, 1] - pts[a, 1]
        L = math.hypot(segx, segy)
        if L <= 0: continue
        sub = pts[a+1:b]
        if len(sub) == 0: continue
        d = np.abs(segx * (sub[:, 1] - pts[a, 1]) - segy * (sub[:, 0] - pts[a, 0])) / L
        k = int(np.argmax(d))
        if d[k] > eps:
            kk = a + 1 + k
            keep[kk] = True
            stk.append((a, kk)); stk.append((kk, b))
    return pts[keep]

blk = json.load(gzip.open(OUT))
paths = [parse(p) for p in blk['ps']]
N0 = sum(len(p) for p in paths)
target = int(N0 * FRAC)

def total_for(eps):
    return sum(len(dp_ring(p, eps)) for p in paths)

# recherche dichotomique de eps
lo, hi = 0.0002, 0.004
for _ in range(14):
    mid = (lo + hi) / 2
    t = total_for(mid)
    if t > target: lo = mid
    else: hi = mid
eps = (lo + hi) / 2

out = []
tot = 0
for p in paths:
    m = dp_ring(p, eps)
    if len(m) < 5: m = p
    s = ''
    for k, q in enumerate(m):
        s += ('M' if k == 0 else 'L') + ('%.5f %.5f' % (q[0], q[1]))
    tot += len(m)
    out.append(s + 'Z')

blk['ps'] = out
blk['pts'] = tot
blk['methode'] = (blk.get('methode', '') + '-simp%dpct' % round(100 * tot / N0))
with gzip.open(OUT, 'wb') as f:
    f.write(json.dumps(blk).encode())
print('eps retenu %.5f : %d -> %d points (%.1f%%)' % (eps, N0, tot, 100.0 * tot / N0))