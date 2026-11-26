# Norvège (NO) — VALIDÉE (26/11/2026)

## Résultat
- Bloc final: out/final/NO.json.gz — 305 boucles, 256 654 pts, simplifié à 75 % (eps 0.00070), 1,6 Mo.
- Méthode: coastvec géométrique + îles vectorielles (le raster continental avait échoué: fjords non inondés).
- Continental: 295 155 km², 1 759 097 pts bruts, assemblé depuis 54 522 ways côtes + 103 ways frontière terrestre L2 Norge, ZÉRO corde nécessaire (graphe eulérien parfait après élagage).
- Îles: 304 îles ≥ 5 km² (seuil Fabrice), 80 907 km² — Svalbard (Spitsbergen, Nordaustlandet…), Jan Mayen (372,8 km²), Senja, Hinnøya, Tromsøya, Kvaløya…
- Sondes: 21/21 OK (Oslo, Bergen, Trondheim, Alta, Tromsø, Hammerfest, Longyearbyen, Senja, Hinnøya, Jan Mayen TERRE ; Sognefjord, Skagerrak, mer de Norvège, Kiruna, Mourmansk EAU).

## HTML
- node tools/v9html.js out/europe-v10-test.html → 39 pays, 17,9 Mo, viewer validé (new Function), noms FR au survol (table FRN).

## Leçons clés (v9coastvec_no.py)
1. gkey: (lon*1e4 << 22) | lat*1e4 — bug historique de double multiplication ×10000 (débordement 22 bits).
2. Des nodes OSM distincts existent au même point géographique (Svinesund 9391463739/40162818) → assemblage GÉOMÉTRIQUE par gkeys arrondis + clustering 30 m indispensable.
3. Le filtre len(refs)<3 cassait la chaîne côtière (connecteurs à 2 refs) — garder les ways ≥ 2 refs.
4. Les « coastlines » de rivières (Altaelva) pendent de la côte → élaguer les branches de degré 1 (prune_dangling), sinon cordes parasites qui inversent la parité (bandes côtières rendues EAU).
5. Les comps ouvertes (fragments) ne doivent PAS être eulérisées par cordes (îles factices couvrant la mer) → seules les comps fermées deviennent des îles; seul le continental (contenant la frontière) a droit aux cordes.
6. Ne pas cicatriser près des extrémités frontalières (Svinesund/Jakobselv) sinon absorption de côtes suédoise/russe.
7. float32 ok pour le stockage des anneaux (rings-no.npz) mais cast float64 obligatoire pour le shoelace (annulation catastrophique).
8. pop(best) confondait position et valeur dans la liste (appariement des odds) — corrigé.
9. Bug scanline historique: coordonnées déjà en cellules, ne pas re-diviser par ENV_STEP.

## Sauvegardes locales
- out/backup/NO-continental.json.gz (raster, rejeté), NO-post-iles-raster.json.gz, NO-final-coastvec.json.gz (pré-simplification, 305 boucles / 342 152 pts).
- out/work/rings-no.npz: 96 289 anneaux bruts (7 M pts).

## Manifeste: 39/39 blocs livrés (38 pays workflow + NO)
AL AT BA BE BG BY CH CY CZ DE DK EE ES FR GB GR HR HU IE IS IT LT LU LV MD ME MK MT NL NO PL PT RO RS SE SI SK UA XK
