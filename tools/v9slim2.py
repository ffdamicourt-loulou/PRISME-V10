# v9slim2.py <ISO> — réduit data/<ISO>/nodes.json.gz aux nodes requis
# (refs des ways natural=coastline + ways des anneaux land9), en flux continu
# (mémoire ~négligeable : un bytearray de N octets).
import gzip, json, sys, os, shutil

ISO = sys.argv[1]
D = '/home/user/artifacts/v9/data/%s/' % ISO

ways = json.load(gzip.open(D + 'ways.json.gz'))
need = set()
land9w = set()
try:
    l9 = json.load(gzip.open(D + 'land9.json.gz'))
    for ring in l9.get('rings', []):
        for wid, rev in ring:
            land9w.add(abs(wid))
except FileNotFoundError:
    pass
for w in ways:
    if (w.get('tags') or {}).get('natural') == 'coastline' or w['id'] in land9w:
        need.update(w['refs'])
print(ISO, 'nodes requis:', len(need))

if not os.path.exists(D + 'nodes-full.json.gz'):
    shutil.copy(D + 'nodes.json.gz', D + 'nodes-full.json.gz')
SRC = D + 'nodes-full.json.gz'


def iter_nums(key):
    """yield chaque nombre (str) du tableau "key":[ ... ] en flux continu."""
    with gzip.open(SRC, 'rt') as f:
        started = False
        buf = ''
        while True:
            chunk = f.read(1 << 20)
            if not chunk and not buf:
                return
            buf += chunk
            if not started:
                i = buf.find('"%s":[' % key)
                if i < 0:
                    buf = buf[-64:]
                    if not chunk:
                        return
                    continue
                buf = buf[i + len(key) + 4:]
                started = True
            endarr = False
            body = buf
            if ']' in buf:
                body = buf[:buf.find(']')]
                endarr = True
            else:
                k = body.rfind(',')
                if k >= 0 and not chunk:  # fin de fichier improbable
                    endarr = True
                elif k >= 0:
                    body, part = body[:k], body[k + 1:]
                    buf = part
                    for tok in body.split(','):
                        tok = tok.strip().lstrip('[').rstrip(']')
                        if tok:
                            yield tok
                    continue
            for tok in body.split(','):
                tok = tok.strip().lstrip('[').rstrip(']')
                if tok:
                    yield tok
            if endarr:
                return
            if not chunk:
                return


# passe 1 : masque des positions gardées
keep = bytearray(1 << 28)
n = 0
nk = 0
for tok in iter_nums('ids'):
    keep[n] = 1 if int(tok) in need else 0
    nk += keep[n]
    n += 1
print('ids scannés:', n, 'gardés:', nk)
if nk == 0:
    sys.exit('ERREUR: aucun node gardé')

# passe 2 : écriture
out = gzip.open(D + 'nodes.json.gz', 'wb')
for key in ('ids', 'lons', 'lats'):
    out.write(('{"ids":[' if key == 'ids' else '],"lons":[' if key == 'lons' else '],"lats":[').encode())
    i = 0
    first = True
    for tok in iter_nums(key):
        if keep[i]:
            out.write(('' if first else ',').encode())
            out.write(tok.encode())
            first = False
        i += 1
out.write(b']}')
out.close()
print('nodes.json.gz réécrit (%d nodes)' % nk)