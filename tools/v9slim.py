# v9slim.py <ISO> : reduit data/<ISO>/nodes.json.gz aux nodes references par
# les ways natural=coastline + les ways des anneaux land9 (masque admin).
# Le reste (nodes des ways non retenus) est inutile a v9land/v9isles.
import gzip, json, sys
ISO = sys.argv[1]
D = '/home/user/artifacts/v9/data/%s/' % ISO
ways = json.load(gzip.open(D + 'ways.json.gz'))
keep = set()
for w in ways:
    t = w.get('tags') or {}
    if t.get('natural') == 'coastline': keep.update(w['refs'])
try:
    land9 = json.load(gzip.open(D + 'land9.json.gz'))
    for ring in land9.get('rings', []):
        for wid, rev in ring: keep.add(abs(wid))
except FileNotFoundError:
    pass
wids = set()
for w in ways:
    if w['id'] in keep or (w.get('tags') or {}).get('natural') == 'coastline': wids.add(w['id'])
nids = set()
for w in ways:
    if w['id'] in wids: nids.update(w['refs'])
N = json.load(gzip.open(D + 'nodes.json.gz'))
ids, lons, lats = N['ids'], N['lons'], N['lats']
out = {'ids': [], 'lons': [], 'lats': []}
for i, x in enumerate(ids):
    if x in nids:
        out['ids'].append(x); out['lons'].append(lons[i]); out['lats'].append(lats[i])
print('%s: nodes %d -> %d ; ways refs %d' % (ISO, len(ids), len(out['ids']), len(nids)))
import os, shutil
if not os.path.exists(D + 'nodes-full.json.gz'):
    shutil.copy(D + 'nodes.json.gz', D + 'nodes-full.json.gz')
with gzip.open(D + 'nodes.json.gz', 'wb') as f:
    f.write(json.dumps(out).encode())