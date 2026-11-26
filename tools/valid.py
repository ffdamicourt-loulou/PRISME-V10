#!/usr/bin/env python
# valid.py — validation d'un bloc final : points dans le pays / hors du pays + aire approx
#   python valid.py <ISO>
import sys, gzip, json, math
import numpy as np
ISO = sys.argv[1]
B = '/home/user/artifacts/v9/out/final/%s.json.gz' % ISO
with gzip.open(B) as f: blk = json.load(f)
paths = []
for d in blk['ps']:
    pts = []
    for seg in d[:-1].split('L'):
        if seg[0] == 'M': seg = seg[1:]
        x, y = seg.split(' ')
        pts.append((float(x), float(y)))
    paths.append(np.array(pts))
INV = lambda y: math.degrees(math.atan(math.sinh(math.radians(y))))
YC = 0.74

def inside(lon, lat):
    x = lon; y = math.degrees(math.asinh(math.tan(math.radians(lat))))
    inside_any = False
    for p in paths:
        # pip avec tolerance : anneau fermé
        px, py = p[:,0], p[:,1]
        qx, qy = np.roll(px, -1), np.roll(py, -1)
        cond = (py <= y) & (qy > y) | (qy <= y) & (py > y)
        if not cond.any(): continue
        xi = px[cond] + (y - py[cond]) * (qx[cond] - px[cond]) / (qy[cond] - py[cond])
        inside_any ^= int((xi < x).sum()) % 2 == 1
    return bool(inside_any)

TESTS = {
 'HR': [(15.97,45.81,'Zagreb',True),(16.44,43.51,'Split',True),(16.19,43.16,'Hvar',True),
        (16.65,45.23,'ZagrebE',True),(14.4,44.97,'Cres',True),(18.09,42.65,'Dubrovnik',True),
        (17.0,42.92,'sommet LastovoÏ',False),(18.5,42.6,'mer DubrovnikS',False),
        (13.3,45.48,'Savudrija',True),(17.15,45.09,'Osijek',True),(13.2,44.9,'mer NW Istrie',False),
        (15.0,44.9,'Crikvenica',True),(16.9,43.0,'Mljet?',True),(16.25,43.98,'Zadar',True),
        (17.68,42.91,'Neum(BA)',False),(16.75,45.47,'S Daruvar',True),(15.5,45.3,'Zaprešić',True),
        (16.4,44.2,'Dinara',True),(18.7,45.55,'mer/BA est',False),(19.4,45.1,'RS/BA',False)],
 'GR': [(23.73,37.98,'Athènes',True),(22.94,40.64,'Thessalonique',True),(25.13,35.33,'Héraklion',True),
        (28.22,36.44,' Rhodes',True),(26.1,38.4,'mer Égée N',False),(23.0,41.0,'Grèce N',True),
        (20.0,39.5,'mer Ioannine O',False),(26.5,39.0,'mer Égée',False),(24.5,35.2,'Crète S',False),
        (22.5,37.0,'mer Corinthie',False),(23.7,41.0,'Flórina',True),(28.0,41.0,'mer Thrace',False)],
}
tests = TESTS.get(ISO)
fails = 0
if tests:
    for x, y, name, want in tests:
        got = inside(x, y)
        st = 'OK ' if got == want else 'ECHEC'
        if got != want: fails += 1
        print('%s %-22s %s' % (st, name, 'dans' if got else 'hors'))
print('boucles', len(paths), 'points', sum(len(p) for p in paths), 'fails', fails)