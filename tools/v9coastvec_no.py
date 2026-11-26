#!/usr/bin/env python
# v9coastvec_no.py (v2) — SILHOUETTE VECTORIELLE de la Norvege, ASSEMBLAGE GEOMETRIQUE:
#   - endpoints de ways identifies par clef (lon,lat) arrondie ~1e-4 deg (10 m):
#     les nodes OSM distincts mais confondus geographiquement se soudent.
#   - composantes: cotes NO (filtre masque envelope land9 + Svalbard/Jan Mayen)
#     + frontieres TERRESTRES de la relation L2 Norge (ways non maritime).
#   - composantes eulerisees par PONTS (corde droite) entre pairs de nodes impairs
#     les plus proches -> chaque comp devient un anneau ferme (chords aux breches).
#   - mainland = plus grand anneau; les autres = iles (seuil km2, KEEP).
import sys, gzip, json, math, os, time, re
import numpy as np
from collections import defaultdict

EPS = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0005
KEEP = float(sys.argv[2]) if len(sys.argv) > 2 else 0.65
MIN_KM2 = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0

D = '/home/user/artifacts/v9/data/NO/'
BD = D + 'bin/'
OUT = '/home/user/artifacts/v9/out/final/NO.json.gz'
T0 = time.time()

wids = np.fromfile(BD + 'eways_ids.bin', dtype=np.int64)
woff = np.fromfile(BD + 'eways_off.bin', dtype=np.int64)
wrefs = np.fromfile(BD + 'eways_refs.bin', dtype=np.int64)
wcoast = np.fromfile(BD + 'eways_coast.bin', dtype=np.int64).astype(np.uint8)
if wcoast.dtype != np.uint8 or len(wcoast) != len(wids):
    wcoast = np.fromfile(BD + 'eways_coast.bin', dtype=np.uint8)
assert len(wcoast) == len(wids), 'bins incoherents'
order = np.argsort(wids); wsorted = wids[order]
z = np.load(D + 'nodes.npz'); nids, nlons, nlats = z['ids'], z['lons'], z['lats']

def node_ll(nd):
    j = np.searchsorted(nids, nd)
    if j >= len(nids) or nids[j] != nd: return None
    return float(nlons[j]), float(nlats[j])

def node_lls(arr):
    j = np.searchsorted(nids, arr)
    bad = (j >= len(nids)) | (nids[j] != arr)
    if bad.any(): return None
    return nlons[j], nlats[j]

def gkey_of_nd(arr):
    c = node_lls(arr)
    if c is None: return None
    lo = np.round(c[0] * 10000).astype(np.int64)
    la = np.round(c[1] * 10000).astype(np.int64)
    return (lo << 22) | (la & ((1 << 22) - 1))

def gkey_toll(k):
    lo = float(k >> 22) / 10000.0
    la = float(k & ((1 << 22) - 1)) / 10000.0
    return lo, la

def ix_of(wid):
    j = np.searchsorted(wsorted, wid)
    if j >= len(wsorted) or int(wsorted[j]) != wid: return None
    return int(order[j])

def rl_of(i): return wrefs[woff[i]:woff[i + 1]]

# --- relation L2 Norge + tags maritime
rels = json.load(gzip.open(D + 'rels.json.gz'))
relno = [r for r in rels if r.get('level') == 2 and r.get('iso1') == 'NO'][0]
l2ways = [m['id'] for m in relno['members'] if m.get('t') == 1]
txt = gzip.open(D + 'ways.json.gz').read().decode()
wset = set(l2ways); maritime = set()
for m in re.finditer(r'\{"id":(\d+),"refs":\[[^\]]*\],"tags":(\{[^}]*\})\}', txt):
    if int(m.group(1)) in wset and 'maritime' in m.group(2): maritime.add(int(m.group(1)))
del txt
landways = []
for wid in l2ways:
    if wid in maritime: continue
    i = ix_of(wid)
    if i is not None and len(rl_of(i)) >= 2: landways.append(i)
print('frontieres terrestres:', len(landways), '(%.0fs)' % (time.time() - T0))

# --- enveloppe territoriale : anneaux ORDONNES de land9.json.gz -> masque raster
land9 = json.load(gzip.open(D + 'land9.json.gz'))
envrings = []
for ring in land9['rings']:
    pts = None; ok = True
    for wid, rev in ring:
        i = ix_of(wid)
        if i is None: ok = False; break
        r = rl_of(i)
        if rev: r = r[::-1]
        c = node_lls(r)
        if c is None: ok = False; break
        cc = np.column_stack(c)
        pts = cc if pts is None else np.vstack([pts, cc[1:]])
    if ok and pts is not None and len(pts) >= 8: envrings.append(pts)
print('cycles enveloppe (land9): %d (%.0fs)' % (len(envrings), time.time() - T0))

ENV_STEP = 0.01
allv = np.vstack(envrings)
lon0, lon1 = float(allv[:, 0].min()) - 0.3, float(allv[:, 0].max()) + 0.3
lat0, lat1 = float(allv[:, 1].min()) - 0.3, float(allv[:, 1].max()) + 0.3
nx = int((lon1 - lon0) / ENV_STEP) + 1
ny = int((lat1 - lat0) / ENV_STEP) + 1
mask = np.zeros((ny, nx), dtype=bool)
for r in envrings:
    gx0 = (r[:, 0] - lon0) / ENV_STEP; gy0 = (r[:, 1] - lat0) / ENV_STEP
    xa = gx0; xb = np.roll(gx0, -1); ya = gy0; yb = np.roll(gy0, -1)
    rowA = np.floor(np.minimum(ya, yb)).astype(np.int64)
    rowB = np.floor(np.maximum(ya, yb)).astype(np.int64)
    keep = (rowB > rowA) & (rowA >= 0) & (rowB < ny)
    rowA, rowB, xa, xb, ya, yb = rowA[keep], rowB[keep], xa[keep], xb[keep], ya[keep], yb[keep]
    counts = rowB - rowA
    if counts.sum() == 0: continue
    rows = np.repeat(np.arange(len(counts)), counts)
    offs = np.arange(counts.sum()) - np.repeat(np.cumsum(counts) - counts, counts)
    rr = rowA[rows] + offs + 0.5
    t = (rr - ya[rows]) / (yb[rows] - ya[rows])
    xx = xa[rows] + t * (xb[rows] - xa[rows])
    key = rr * 1e9 + xx
    o = np.argsort(key); rr, xx = rr[o], xx[o]
    brk = np.flatnonzero(np.diff(rr) != 0)
    starts = np.concatenate([[0], brk + 1]); ends = np.concatenate([brk + 1, [len(rr)]])
    for s, e in zip(starts, ends):
        xs = xx[s:e]
        for k in range(0, len(xs) - 1, 2):
            c0 = max(0, min(nx - 1, int(math.floor(xs[k]))))
            c1 = max(0, min(nx - 1, int(math.ceil(xs[k + 1]))))
            mask[int(rr[s]), c0:c1 + 1] = True
print('masque enveloppe: %.2f%% (%.0fs)' % (100.0 * mask.mean(), time.time() - T0))

def in_mask(lon, lat):
    gx = int((lon - lon0) / ENV_STEP); gy = int((lat - lat0) / ENV_STEP)
    if gx < 0 or gy < 0 or gx >= nx or gy >= ny: return False
    return bool(mask[gy, gx])

def EXCEPT(lo, la):
    if la > 74.0 and 10.0 <= lo <= 34.0: return True
    if -10.0 <= lo <= -6.5 and 70.4 <= la <= 71.2: return True
    return False

# --- cotes norvegiennes: masque STRICT (midpoint) puis cicatrisation des coupures
ci = np.nonzero(wcoast == 1)[0]
mid_nd = np.array([int(wrefs[(woff[i] + woff[i + 1]) // 2]) for i in ci], dtype=np.int64)
mc = node_lls(mid_nd)
keepc = set(); exclu = []
for k in range(len(ci)):
    i = int(ci[k])
    if len(rl_of(i)) < 2: continue
    lo, la = float(mc[0][k]), float(mc[1][k])
    if in_mask(lo, la) or EXCEPT(lo, la): keepc.add(i)
    else: exclu.append(i)
print('cotes NO gardees (strict): %d / %d (%.0fs)' % (len(keepc), len(ci), time.time() - T0))
for _pass in range(3):
    keptEnds = set()
    for i in keepc:
        r = rl_of(i)
        ka = gkey_of_nd(np.array([r[0], r[-1]]))
        keptEnds.add(int(ka[0])); keptEnds.add(int(ka[1]))
    # ne pas cicatriser pres des extremites de frontierre (cotes etrangeres)
    if _pass == 0:
        _lpend = {}
        for i in landways:
            r = rl_of(i)
            _lpend[int(r[0])] = _lpend.get(int(r[0]), 0) + 1
            _lpend[int(r[-1])] = _lpend.get(int(r[-1]), 0) + 1
        _endnd = [nd for nd, c in _lpend.items() if c == 1]
        _j = np.searchsorted(nids, np.array(_endnd, dtype=np.int64))
        _borderll = np.column_stack([nlons[_j], nlats[_j]])
    added = 0
    still = []
    for i in exclu:
        k0 = int(wrefs[woff[i]]); k1 = int(wrefs[woff[i + 1] - 1])
        jj = np.searchsorted(nids, np.array([k0, k1], dtype=np.int64))
        skip = False
        for kk in (0, 1):
            dx = (_borderll[:, 0] - float(nlons[jj[kk]])) * 111.32 * math.cos(math.radians(float(nlats[jj[kk]])))
            dy = (_borderll[:, 1] - float(nlats[jj[kk]])) * 110.57
            if (dx * dx + dy * dy).min() < 9.0:
                skip = True; break
        if skip:
            still.append(i); continue
        r = rl_of(i)
        ka = gkey_of_nd(np.array([r[0], r[-1]]))
        if int(ka[0]) in keptEnds or int(ka[1]) in keptEnds:
            keepc.add(i); added += 1
        else:
            still.append(i)
    exclu = still
    print('  cicatrisation passe %d: +%d (restants %d)' % (_pass + 1, added, len(exclu)))
    if added == 0: break
keepc = sorted(keepc)
import gc
for _n in ('gx', 'gy', 'inb', 'refidx', 'ok', 'hit', 'inm'):
    globals()[_n] = None
gc.collect()

allw = list(dict.fromkeys(landways + keepc))
# bridges = cordes droites: (-1, gkA, gkB)
items = {i: ('w',) for i in allw}
# endpoints gkey par way
eA = {}; eB = {}
for i in allw:
    r = rl_of(i)
    ka = gkey_of_nd(np.array([r[0], r[-1]]))
    eA[i] = int(ka[0]); eB[i] = int(ka[1])
byEnd = defaultdict(list)
for i in allw:
    byEnd[eA[i]].append(i)
    if eA[i] != eB[i]: byEnd[eB[i]].append(i)
# extremites de la chaine frontierre terrestre (a souder aux cotes)
degL = defaultdict(int)
for i in landways:
    if eA[i] == eB[i]: degL[eA[i]] += 2
    else: degL[eA[i]] += 1; degL[eB[i]] += 1
landEnds = {g for g in degL if degL[g] == 1}
print('extremites frontierre:', [gkey_toll(g) for g in landEnds])
print('graphe geometrique: %d ways (%.0fs)' % (len(allw), time.time() - T0))

def find_(x, par):
    while par[x] != x: par[x] = par[par[x]]; x = par[x]
    return x
par = {g: g for g in byEnd}
# clustering geometrique: cellules 0.002 deg, toler ~30 m -> union des gkeys voisins
CELL = {}  # cell 0.002 -> [gkeys]
for g in byEnd:
    lo, la = gkey_toll(g)
    CELL.setdefault((int(lo // 0.002), int(la // 0.002)), []).append(g)
for (cx, cy), gl in CELL.items():
    cand = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            cand.extend(CELL.get((cx + dx, cy + dy), []))
    if len(cand) <= 1: continue
    lls = {g: gkey_toll(g) for g in cand}
    for i, ga in enumerate(cand):
        for gb in cand[i + 1:]:
            dx = abs(lls[ga][0] - lls[gb][0]) * 111320 * math.cos(math.radians((lls[ga][1] + lls[gb][1]) / 2))
            dy = abs(lls[ga][1] - lls[gb][1]) * 110570
            if dx * dx + dy * dy < 900:  # <30 m
                ra, rb = find_(ga, par), find_(gb, par)
                if ra != rb: par[ra] = rb
for i in allw:
    ra, rb = find_(eA[i], par), find_(eB[i], par)
    if ra != rb: par[ra] = rb
waycomp = {}
for i in allw:
    waycomp[i] = find_(eA[i], par)
comps = defaultdict(list)
for i in allw: comps[waycomp[i]].append(i)
print('composantes:', len(comps), '(%.0fs)' % (time.time() - T0))

def comp_items(cid):
    """eulerise la composante: renvoie (ways, bridges). Self-loops deg=2."""
    ws = set(comps[cid])
    deg = defaultdict(int)
    for i in ws:
        if eA[i] == eB[i]:
            deg[eA[i]] += 2
        else:
            deg[eA[i]] += 1; deg[eB[i]] += 1
    odds = [g for g in deg if deg[g] % 2 == 1]
    lls = {g: gkey_toll(g) for g in odds}
    def d2(g1, g2):
        a, b = lls[g1], lls[g2]
        dx = (a[0] - b[0]) * math.cos(math.radians((a[1] + b[1]) / 2)) * 111.32
        dy = (a[1] - b[1]) * 110.57
        return dx * dx + dy * dy
    bridges = []
    # 1) souder en priorite les extremites de la chaine frontierre terrestre
    remaining = list(odds)
    for gl in list(remaining):
        if gl not in landEnds: continue
        if gl not in remaining: continue
        best = None; bd = 1e18
        for g2 in remaining:
            if g2 == gl: continue
            d = d2(gl, g2)
            if d < bd: bd = d; best = g2
        if best is not None and bd < 5000 * 5000:
            remaining.remove(gl); remaining.remove(best)
            bridges.append((gl, best))
            items[-len(bridges)] = ('b',)
    # 2) pairs les odds restants par plus proche distance (glouton)
    rem = list(range(len(remaining)))
    while len(rem) >= 2:
        a = rem[0]
        bestpos = None; bd = 1e18
        for pi in range(1, len(rem)):
            j = rem[pi]
            d = d2(remaining[a], remaining[j])
            if d < bd: bd = d; bestpos = pi
        if bestpos is None: break
        j = rem.pop(bestpos)
        rem.pop(0)
        bridges.append((remaining[a], remaining[j]))
        items[-len(bridges)] = ('b',)
    return ws, bridges

def build_ring(ws, bridges, cid):
    """hierholzer sur ways + bridges, renvoie coords (N,2) ou None."""
    badj = defaultdict(list)  # gkey -> [bid,...]
    bmap = {}  # bid -> (a,b)
    bid = -1
    for a, b in bridges:
        bid -= 1
        bmap[bid] = (a, b)
        badj[a].append(bid); badj[b].append(bid)
    adj = {}
    for i in ws:
        adj.setdefault(eA[i], []).append(i)
        if eA[i] != eB[i]: adj.setdefault(eB[i], []).append(i)
    for g, lst in badj.items(): adj.setdefault(g, []).extend(lst)
    def other_end(it, g):
        if it < 0:
            a, b = bmap[it]
            return b if a == g else a
        return eB[it] if eA[it] == g else eA[it]
    st = [eA[next(iter(ws))]]
    out = []
    wset = set(ws) | set(bmap)
    while st:
        v = st[-1]
        nxt = None
        for it in adj.get(v, []):
            if it in wset: nxt = it; break
        if nxt is None:
            out.append(st.pop())
        else:
            wset.discard(nxt)
            st.append(other_end(nxt, v))
    if len(out) < 4 or out[0] != out[-1]: return None
    # cycle de gkeys -> coords
    pts = None
    for a, b in zip(out, out[1:]):
        found = False
        for it in adj.get(a, []):
            if it >= 0:
                if eA[it] == a and eB[it] == b: use = rl_of(it); oa, ob = None, None
                elif eB[it] == a and eA[it] == b: use = rl_of(it)[::-1]
                else: continue
                c = node_lls(use)
                if c is None: return None
                cc = np.column_stack(c)
                pts = cc if pts is None else np.vstack([pts, cc[1:]])
            else:
                ga, gb = bmap[it]
                if ga == a and gb == b: ka, kb = ga, gb
                elif gb == a and ga == b: ka, kb = gb, ga
                else: continue
                c1 = np.array(gkey_toll(ka)); c2 = np.array(gkey_toll(kb))
                cc = np.vstack([c1, c2])
                pts = cc if pts is None else np.vstack([pts, cc[1:]])
            found = True
            break
        if not found: return None
    return pts

rings = []; nfail = 0
done = 0
my_deg = lambda i: 2 if eA[i] == eB[i] else 1
def hierholzer(ws, bridges):
    badj = defaultdict(list); bmap = {}
    bid = -1
    for a, b in bridges:
        bid -= 1
        bmap[bid] = (a, b)
        badj[a].append(bid); badj[b].append(bid)
    adj = defaultdict(list)
    for i in ws:
        adj[eA[i]].append(i)
        if eA[i] != eB[i]: adj[eB[i]].append(i)
    for g, lst in badj.items(): adj[g].extend(lst)
    def other_end(it, g):
        if it < 0:
            a, b = bmap[it]
            return b if a == g else a
        return eB[it] if eA[it] == g else eA[it]
    st = [eA[next(iter(ws))]]
    out = []
    wset = set(ws) | set(bmap)
    while st:
        v = st[-1]
        nxt = None
        for it in adj[v]:
            if it in wset: nxt = it; break
        if nxt is None:
            out.append(st.pop())
        else:
            wset.discard(nxt)
            st.append(other_end(nxt, v))
    if not out or out[0] != out[-1]: return None
    parts = []; prev = None
    for a, b in zip(out, out[1:]):
        found = False
        for it in adj.get(a, []):
            if it >= 0:
                if eA[it] == a and eB[it] == b: use = rl_of(it)
                elif eB[it] == a and eA[it] == b: use = rl_of(it)[::-1]
                else: continue
                c = node_lls(use)
                if c is None: return None
                cc = np.column_stack(c).astype(np.float32)
                parts.append(cc[1:] if parts else cc)
            else:
                ga, gb = bmap[it]
                if not ((ga == a and gb == b) or (gb == a and ga == b)): continue
                cc = np.vstack([np.array(gkey_toll(ga)), np.array(gkey_toll(gb))])
                parts.append(cc[1:] if parts else cc)
            found = True
            break
        if not found: return None
    pts = np.concatenate(parts, axis=0) if parts else None
    if pts is None or len(pts) < 8: return None
    return pts

def prune_dangling(ws):
    """elague les branches pendantes (rivieres, fragments) attaches a un seul point."""
    ws = set(ws)
    adj = defaultdict(list)
    for i in ws:
        adj[eA[i]].append(i)
        if eA[i] != eB[i]: adj[eB[i]].append(i)
    deg = {g: len(l) for g, l in adj.items()}
    from collections import deque
    q = deque(g for g in deg if deg[g] == 1)
    while q:
        g = q.popleft()
        if deg.get(g, 0) != 1: continue
        w = adj[g][0] if adj[g] else None
        if w is None or w not in ws: continue
        ws.remove(w)
        o = eB[w] if eA[w] == g else eA[w]
        if o != g:
            deg[o] -= 1
            if deg[o] == 1: q.append(o)
        deg[g] = 0
    return ws

for cid in list(comps):
    done += 1
    if done % 20000 == 0: print('  comp %d/%d (%.0fs)' % (done, len(comps), time.time() - T0), flush=True)
    ws = comps[cid]
    # cas 1: composante = une seule way fermee (self-loop) -> ring direct
    if len(ws) == 1:
        i = ws[0]
        if eA[i] == eB[i]:
            c = node_lls(rl_of(i))
            if c is not None:
                cc = np.column_stack(c).astype(np.float32)
                if len(cc) >= 8: rings.append(cc)
        continue
    # cas 2: elaguer les branches pendantes puis euleriser
    ws2 = prune_dangling(comps[cid])
    if not ws2: nfail += 1; continue
    comp_ws = ws2
    # bricoler un mini-comps pour reutiliser comp_items: faire deg sur ws2
    deg2 = defaultdict(int)
    for i in ws2:
        if eA[i] == eB[i]: deg2[eA[i]] += 2
        else: deg2[eA[i]] += 1; deg2[eB[i]] += 1
    odds2 = [g for g in deg2 if deg2[g] % 2 == 1]
    has_land = any(wcoast[i] == 0 for i in ws2)
    if odds2 and not has_land:
        # comp ouverte (fragment de cote): pas d'ile factice par corde
        nfail += 1; continue
    lls = {g: gkey_toll(g) for g in odds2}
    def d2(g1, g2):
        a, b = lls[g1], lls[g2]
        dx = (a[0] - b[0]) * math.cos(math.radians((a[1] + b[1]) / 2)) * 111.32
        dy = (a[1] - b[1]) * 110.57
        return dx * dx + dy * dy
    bridges = []
    remaining = list(odds2)
    for gl in list(remaining):
        if gl not in landEnds or gl not in remaining: continue
        best = None; bd = 1e18
        for g2 in remaining:
            if g2 == gl: continue
            d = d2(gl, g2)
            if d < bd: bd = d; best = g2
        if best is not None and bd < 5000 * 5000:
            remaining.remove(gl); remaining.remove(best)
            bridges.append((gl, best))
    rem = list(range(len(remaining)))
    while len(rem) >= 2:
        a = rem[0]
        bestpos = None; bd = 1e18
        for pi in range(1, len(rem)):
            j = rem[pi]
            d = d2(remaining[a], remaining[j])
            if d < bd: bd = d; bestpos = pi
        if bestpos is None: break
        j = rem.pop(bestpos)
        rem.pop(0)
        bridges.append((remaining[a], remaining[j]))
    cc = hierholzer(ws2, bridges)
    if cc is not None: rings.append(cc)
    else: nfail += 1
print('anneaux vectoriels: %d (echecs %d) (%.0fs)' % (len(rings), nfail, time.time() - T0))

WORK = '/home/user/artifacts/v9/out/work/'
os.makedirs(WORK, exist_ok=True)
PHASE = os.environ.get('NPHASE', 'all')
if PHASE in ('asm', 'all'):
    import gc
    for _n in ('par', 'byEnd', 'waycomp', 'comps', 'items', 'CELL', 'hit', 'refidx'):
        globals()[_n] = None
    gc.collect()
    offs = np.cumsum([0] + [len(r) for r in rings])
    flat = np.concatenate(rings, axis=0).astype(np.float32)
    rings = None; gc.collect()
    np.savez_compressed(WORK + 'rings-no.npz', flat=flat, offs=offs)
    print('rings sauvegardes: %d, %d pts (%.0fs)' % (len(offs) - 1, len(flat), time.time() - T0))
    del rings
    if PHASE == 'asm': sys.exit(0)
if PHASE in ('fin', 'all'):
    zz = np.load(WORK + 'rings-no.npz')
    flat = zz['flat'].astype(np.float64); offs = zz['offs']
    rings = [flat[offs[i]:offs[i + 1]] for i in range(len(offs) - 1)]
    print('rings recharges: %d (%.0fs)' % (len(rings), time.time() - T0))

def shoelace_km2(ll):
    lat0r = math.radians((ll[:, 1].max() + ll[:, 1].min()) / 2)
    x = ll[:, 0] * 111.32 * math.cos(lat0r)
    y = ll[:, 1] * 110.57
    return abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2

scored = sorted(((shoelace_km2(ll), ll) for ll in rings), key=lambda t: -t[0])
mainland = scored[0]
print('mainland: %.0f km2, %d pts' % (mainland[0], len(mainland[1])))
MONSTER = 60000
isles = [t for t in scored[1:] if MIN_KM2 <= t[0] <= MONSTER]
nkeep = max(1, int(round(KEEP * len(isles))))
isles = isles[:nkeep]
nbig = sum(1 for t in scored[1:] if t[0] > MONSTER)
print('iles gardees: %d / %d, monstres ecartes: %d (aire %.0f km2)' % (len(isles), len([t for t in scored[1:] if MIN_KM2 <= t[0] <= MONSTER]), nbig, sum(t[0] for t in isles)))

MY = lambda la: math.degrees(math.asinh(math.tan(math.radians(la))))
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

def to_path(ll):
    m = np.column_stack([ll[:, 0], [MY(v) for v in ll[:, 1]]])
    m = dp_simplify(m, EPS)
    if len(m) < 4: return None, 0
    d = ''
    for k, p in enumerate(m):
        d += ('M' if k == 0 else 'L') + str(round(float(p[0]), 5)) + ' ' + str(round(float(p[1]), 5))
    return d + 'Z', len(m)

ps = []; tot = 0
p, n = to_path(mainland[1])
if p: ps.append(p); tot += n
else: print('ERREUR: mainland non converti!')
for km2, ll in isles:
    d, n = to_path(ll)
    if d: ps.append(d); tot += n

blk = json.load(gzip.open('/home/user/artifacts/v9/out/backup/NO-continental.json.gz'))
blk['ps'] = ps
blk['boucles'] = len(ps)
blk['pts'] = tot
blk['iles'] = max(0, len(ps) - 1)
blk['methode'] = 'coastvec+iles'
with gzip.open(OUT, 'wb') as f:
    f.write(json.dumps(blk).encode())
print('BLOC NO: %d boucles, %d pts, methode coastvec+iles (%.0fs)' % (len(ps), tot, time.time() - T0))
