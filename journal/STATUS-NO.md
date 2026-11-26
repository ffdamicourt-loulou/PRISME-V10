# Norvège — état au 26/11/2026 (tour interrompu)

## Ce qui est fait (localement, non encore versionné ici)
- Ré-extraction NO avec NREFT=40 (package v9/data/NO : ways/nodes/rels).
- Optimisation mémoire pour le volume norvégien (7,3 M nodes / 230 210 coast ways) :
  nodes convertis en binaire npz (v9npz.py), ways de côte en fichiers binaires
  (ways2bin.js -> eways_ids.bin / eways_off.bin / eways_refs.bin, refs par offsets).
- v9land.py adapté pour lire ces formats, passes LANDSEED type Oslo 10.75,59.91 +
  Tromsø 18.96,69.66.
- Bloc provisoire NO.json.gz généré (non simplifié).

## En attente
- SIMPLIFICATION DES CÔTES DE NORVÈGE DE 25 % (décision Fabrice) :
  `python tools/v9simplify.py NO 0.75` (garder 75 % des points),
  à lancer dès que le stockage de fichiers de la conversation est déverrouillé.
- Puis îles v9isles NO (EPS 0.0005, KEEP 0.65, MIN_KM2 5.0) pour cohérence v10,
  régénération du HTML (39 pays), commit blocs/NO ici, maj manifeste + zip.
