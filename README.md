# PRISME V10 — dépôt de travail

Carte de l'Europe HTML — silhouettes pays, 1 frontière = 1 tracé (fusion par ID OSM).

## Arborescence
- `tools/` : pipeline (run9.sh, dl.sh, extract.js [patch NREFT], v9ring.js, v9n1.js, v9land.py [LANDSEED], v9isles.py [seuil 5 km²], v9simplify.py, v9html.js, valid.py...)
- `blocs/<ISO>.json.gz.b64` : blocs pays {iso,nom,ps:[paths mercator],b,boucles,pts,methode} (base64). Les fichiers >1 Mo sont découpés en `.part-aa/ab/...` : recat avant décodage.
- `manifeste.txt`, `journal/KNOWLEDGE.md` : journal complet du projet.

## Restaurer
```bash
base64 -d <ISO>.json.gz.b64 > <ISO>.json.gz     # (+ cat des part-* en un seul .b64 avant)
```
Placer les blocs dans `out/final/` puis `node tools/v9html.js out/europe-v10.html`.

## État
- 38 pays livrés (26/11), seuil îles 5 km², continentains intouchés, HTML 16,6 Mo.
- En cours : Norvège (NREFT=40 ré-extraction, LANDSEED Oslo+Tromsø).
