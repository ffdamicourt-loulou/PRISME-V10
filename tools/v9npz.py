#!/usr/bin/env python3
# v9npz.py — convertit data/<ISO>/nodes.json.gz en nodes.npz (binaire trié, sans liste Python)
#   python v9npz.py <ISO>     (utilisé pour les gros packages: NO...)
import sys, gzip, numpy as np
ISO = sys.argv[1]; D = '/home/user/artifacts/v9/data/' + ISO
raw = gzip.open(D + '/nodes.json.gz').read()
arr = {}
for k in ('ids', 'lons', 'lats'):
    i = raw.index(('"%s":[' % k).encode())
    j = raw.index(b']', i)
    arr[k] = np.fromstring(raw[i + len(k) + 4:j].decode(), dtype=np.float64, sep=',')
ids = arr['ids'].astype(np.int64)
o = np.argsort(ids)
np.savez_compressed(D + '/nodes.npz', ids=ids[o], lons=arr['lons'][o], lats=arr['lats'][o])
print('npz OK:', len(ids), 'nodes')
