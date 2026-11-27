
## 27/11 (4) — Micro-îles < 5 km² supprimées (tous pays)

- **Demande** : supprimer tous pays confondus les îles de moins de 5 km², avec compte rendu du nombre supprimé.
- **Passe 1 annulée** : v9micro.js v1, parseur cassé sur le format SVG « L x y » espacé (FR/HR) → NaN → aires garbage → restauration depuis out/backup/*-pre-microiles.json.gz.
- **v9micro2.js (3 passes par pays, robustes)** : scan (boucles < 5 km², shoelace anneau fermé, conversion ylat AVANT l'aire), cover (centroïde vs grandes boucles de TOUS les pays, pip Float32Array décimé ×4 anneau fermé), drop (îles = non couvertes ; enclaves et îles de lacs = couvertes donc conservées). Backups *-pre-microiles-v2.json.gz.
- **Résultat : 2 544 îles supprimées, 149 658 points retirés** — DK 860, IE 942, PT 535, IS 125, HR 51, FI 29, FR 2. Enclaves intactes : Baarle-Hertog (BE 21), Baarle-Nassau (NL), Venn (DE 5), Brčko (BA 1), fragments Llívia (FR). UA 2 et CY 4 couvertes, conservées. RU déjà nettoyé (216 îles la veille).
- **Blocs** : DK 900→40 boucles, IE 958→16, PT 549→14, IS 127→2, FI 111→82, HR 106→55, FR 17→15. Sondes capitales OK.
- **HTML** : 17,86 Mo, 41 pays, régénéré. GitHub : DK/IE/PT/IS/FI/HR/FR .json.gz.b64 poussés (tailles vérifiées : DK 1 712 462, IE 1 903 430, IS 1 465 420).
- **TODO v11** : Chypre divisée grec/turc (ligne verte OSM).
