# SAUVEGARDE PRISME V10 — référence -REVISION-2811c (28/11/2026)

Contenu de `parts/` : archive `prisme-v10c.tar.gz` (38 217 069 octets, md5 c6c077fa4a8c6afd653ebda3873b72dc) découpée en 37 parties de 1 Mo, encodées base64 (`part_000.b64` … `part_036.b64`).

## Restauration
```bash
cat parts/part_*.b64 | tr -d '\n' | base64 -d > prisme-v10c.tar.gz
md5sum prisme-v10c.tar.gz   # doit donner c6c077fa4a8c6afd653ebda3873b72dc
mkdir restauration && tar xzf prisme-v10c.tar.gz -C restauration
```

## Contenu de l'archive
- `data/eu-fin/` : 41 blocs fin Europe (prisme-v10/blocs) — état carte plein -REVISION-2811b (28/11 (26)).
- `data/as-fin/` : 47 blocs fin Asie (asia/out/final) — idem, RU = Russie d'Asie (RUA).
- `data/eu-lod/` : 41 fichiers LOD Europe (v9/out/lod) {iso,nom,L:[L0,L1,L2]}.
- `data/as-lod/` : 47 fichiers LOD Asie (asia/out/lod).
- `data/merged/` : RUS.json.gz (calque fin), RUSas.json.gz, RUSlod.json.gz (calque LOD, état 2811c rusfix), RUSaslod.json.gz.
- `tools/` : tous les outils du pipeline (générateurs aeulodhtml/alodhtml/a1html/aeuhtml avec filets 0.052, alod, ruoutline, cutstrip, restore2811b/2811c, simlod, etc.).
- `docs-STATUS-ASIE.md`, `docs-KNOWLEDGE.md` : journaux complets.

## Régénération des cartes depuis ces données
```bash
# placer data/eu-fin -> prisme-v10/blocs, data/as-fin -> asia/out/final,
# data/eu-lod -> v9/out/lod, data/as-lod -> asia/out/lod, data/merged -> asia/out/merged
node tools/aeuhtml.js  europe-asie-v10.html      # carte plein (29,9 Mo)
node tools/aeulodhtml.js europe-asie-v10-lod.html  # carte LOD référence (25,7 Mo, filets 0.052)
```
RÉFÉRENCE du projet (décision Fabrice 28/11 (32)) : carte LOD -REVISION-2811c, filets blancs frontières DOUBLÉS (sw 0.052).
