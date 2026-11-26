# Finlande (FI) — VALIDÉE (26/11/2026)

## Résultat
- Bloc final: out/final/FI.json.gz — 95 boucles / 54 795 pts, méthode land:244m+iles, 280 Ko.
- Continental: LANDSEED raster DX 0.0022, 1 boucle / 15 505 pts, terre estimée 324 879 km² (85,44 % du masque). Graines: Tampere, Jyväskylä, Rovaniemi, Lappeenranta.
- Îles: v9isles_no.py FI 0.0005 0.65 5.0 → 94 îles / 3 796 km² (Fasta Åland/Mariehamn, Kimitoön, Hailuoto...).
- Sondes: 14/14 OK (Tampere, Rovaniemi, Ivalo, Saimaa, Mariehamn/Åland, Kimito, Hailuoto TERRE ; golfes de Botnie et de Finlande, mer d Åland, Stockholm, Uppsala, Tromsø EAU).
- Artefact standard accepté: Helsinki, Oulu, Vaasa (villes côtières en frange) = EAU au pixel près, effet Douglas-Peucker, identique à Stockholm/Palerme.

## Pipeline
1. bash tools/run9.sh FI finland 4 (PBF Geofabrik finland, extraction 2,4,6, land9 19 anneaux)
2. node tools/ways2bin.js + python v9npz.py FI (indispensable: le JSON complet OOM)
3. CHANELS=0 ISLES=0 LANDSEED=1 python -u tools/v9land.py FI 0.0022 0.0005 "23.76,61.50;25.67,62.24;25.73,66.50;28.19,61.06"
4. python -u tools/v9isles_no.py FI 0.0005 0.65 5.0 (v9isles.py OOM sur ways.json.gz, la variante bins/npz passe)
5. v9html.js: FRN + FI:Finlande (le HTML 39 pays n avait pas le nom FR de FI, corrigé)

HTML: europe-v10-test.html 18,2 Mo, 40 pays, viewer new Function OK, noms FR (Finlande présente).
Reassemblage FI: base64 -d < blocs/FI.json.gz.b64 > FI.json.gz (280 Ko).
Manifeste 40/40: AL AT BA BE BG BY CH CY CZ DE DK EE ES FI FR GB GR HR HU IE IS IT LT LU LV MD ME MK MT NL NO PL PT RO RS SE SI SK UA XK
