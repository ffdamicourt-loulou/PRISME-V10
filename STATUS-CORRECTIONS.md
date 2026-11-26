# Corrections carte Europe (26/11 soir, tour « A CORRIGER »)

Corrections enregistrées une par une (backup out/backup/ + validation pip + push GitHub), à la demande de Fabrice.

| # | Demande | Diagnostic | Correctif | État |
|---|---------|-----------|-----------|------|
| 1 | Blanc Suisse-Autriche | Liechtenstein absent (convention : LI→CH) | Annexe LI dans bloc CH (Suite 19) | ✅ 15:33 |
| 2 | Blanc Croatie-Serbie | district Brčko (BA) mal couvert par HR | pocket FR/HR/AL + BA vérifié | ✅ 16:10 |
| 3 | Blanc Monténégro-Albanie | anneau ME raster imprécis | ME relring L2 exact (13 332 pts) | ✅ 15:35 |
| 4 | Blanc Albanie-Macédoine | anneaux AL (dissolution) et MK (ancien) ne se joignaient pas (~10 km) | MK = land9 L2 exact (v9land9ring.py 0.0003, 3 314 pts, aire 25 443 km²) + AL = L2 exact (v9n1.js AL l2, 8 612 pts) ; frontière partagée = mêmes ways OSM, zéro blanc | ✅ ce commit |
| 5 | Blanc Lettonie-Estonie | bloc LV raster imprécis côté nord (EE déjà exact) | LV = tracé L2 exact (v9n1.js LV n1, 1 boucle, 37 397 pts) ; frontière LV-EE vérifiée point par point : mêmes ways OSM, zéro blanc (sondes méridiens 24.5→27.5 identiques des deux côtés) | ✅ 26/11 soir |
| 6 | Andorre → intégrer à la France | AD manquant | Annexe AD dans bloc FR (demande Fabrice) | ✅ 16:10 |
| 7 | Côte sud Ukraine trop simplifiée | raster land:244m | UA adminring eps=0.0003 (64 070 pts, Crimée/mer Noire/Danube exacts) | ✅ 16:01 |
| 8 | Chypre trop simplifiée | ancien bloc grossier + Karpas manquant (côte sud du Karpas absente du graphe OSM) | CY = adminring L2 (5 anneaux, enclaves britanniques incluses) + anneau côtier 26 007 pts ; 17/17 sondes OK, Karpas complet | ✅ ce commit |
| 9 | Côte nord Allemagne trop simplifiée | raster | DE adminring eps=0.0003 (71 973 pts, Rügen/Sylt/Heligoland OK) | ✅ 16:05 |
| 10 | Côte nord Pologne trop simplifiée | raster | PL adminring eps=0.0003 (56 589 pts, Wolin/Gdansk OK) | ✅ 16:00 |
| 11 | Irlande : NI→GB, sud indépendant | IE couvrait toute l'île ? | Vérifié : IE = République seule (Donegal/Cork/Dublin), NI (Belfast/Derry/Armagh/Newry) dans GB | ✅ déjà conforme |
| 12 | Frontière sud Estonie trop simplifiée | raster | EE adminring (cf. #5) | ✅ 16:00 |

Autres passes ce tour : FI coastvec+iles+aland (bloc 16:35, sondes 6/6 OK, Helsinki/Oulu/Mariehamn/Rovaniemi TERRE, golfe de Botnie BLANC), GB +annexe NI (15:33), CH +annexe LI (15:33).

Bloc HR enregistré (106 boucles, backup HR-post-iles-vectoriel.json.gz, sondes Zagreb/Split/Dubrovnik/Rijeka/Hvar-est/Korcula/Lastovo OK). Restants connus (mineurs, hors liste A CORRIGER) : lacunes OSM réelles dans le PBF croate (côte fragmentée : Vir = 1 seul way), îles non couvertes Mljet (98 km2), Ouest-Hvar, Scedro, Iz, Ugljan, Vir (~240 km2 au total) ; anomalie préexistante ps[2] (boucle 1610 km2 couvrant un peu de mer entre Korcula et Dubrovnik). Régénération HTML + zip : en cours.

# 26/11 soir (suite) — RUSSIE ajoutée (41 pays) + Kaliningrad cousu

- **Russie d'Europe intégrée** : bloc RU (41e pays) construit depuis hyperknot/country-levels-export (geojson/high/iso2/RU, 43 sujets fédéraux, précision 0.001°, récupérés via tools.github_app.get_file_contents ≤1 Mo, par lots de ~13 à cause du budget 60 s de run_typescript). Dissolution des frontières inter-sujets par annulation d'arêtes exactes (141 441→63 000 paires annulées), rechaînage, clip au méridien 41.55 (Sutherland–Hodgman), filtre terre François-Joseph (merc-Y>102.33, 1 anneau de 18 pts droppé pour ne pas casser le cadrage Nordkapp). Bloc final : **494 boucles, 39 990 pts**, bbox lon 19.80–41.55 / merc 48.08–99.30 (Kola).
- **Kaliningrad** : l'anneau « high » de hyperknot est CORROMPU (bande côtière ouest absente : Zelenogradsk/Pionersky/Nesterov/Sovetsk non couverts, fragments dégénérés de 4–89 pts). Correctif : **anneau cousu (tools/v9kgd.js, 7 317 pts)** = frontières PL→RU (bloc PL exact, 606 pts) + LT→RU (bloc LT exact, 6 663 pts) + côtes hyperknot « medium » (47 pts, topologiquement complet, grossier ~1–2 km). Zéro seam avec PL/LT (mêmes ways OSM), sondes KGD toutes OK (Kaliningrad, Zelenogradsk, Yantarny, Baltiysk, Morskoe, Gusev, Ozersk, Chernyakhovsk, Bagrationovsk ; Pionersky à ~1 km dans la mer = coarseness côtes medium, restant mineur). 1 micro-croisement (30 m) à la couture lagon de Vistule, invisible.
- **Blanc Lettonie–Estonie (coin Petchory)** : comblé — le blanc restant était la Russie (raïon de Petchory). Sondes Petchory/Pytalovo/Ostrov/Sebezh/Pskov/St-Pétersbourg/Moscou/Mourmansk/Sotchi/Krasnodar → RU OK. Carte ASCII blancs région baltique : intérieur des terres 100 % couvert, les # restants = mer uniquement (Baltique, golfe de Finlande, golfe de Riga, mer Blanche).
- **HTML** : out/europe-v10-test.html régénéré, **19.6 Mo, 41 pays**, bbox -31.27 31.51 41.55 102.33 (X1 passe de 40.23 à 41.55 : coupe méridienne Est de la Russie), 41 blocs gzip-base64 + 1 script JS (4 114 octets, new Function OK), FRN+RU:'Russie'.
- Restants connus RU : ~60 cellules-trous micro (~150 km², Kola/Ladoga/Rostov), fringe eaux territoriales (golfe de Finlande, baie de Taganrog), Pionersky (côtes medium), îles HR déjà connues.

# 26/11 nuit — BLANC GOLFE DE RIGA COMBLÉ + barres aperçu éliminées (EE rel 79510, FI rel 54224)

- **Zone blanche golfe de Riga (analyse)** : le bloc EE n'était PAS corrompu (rel 79510 exact, 1 anneau 11 000 pts) — le blanc venait d'une INCOHÉRENCE OSM : la ligne maritime EE-LV du golfe existe en 2 versions, simplifiée (ways 993983039+040, 11 pts, dans la rel EE) et détaillée (way 993983041, 268 pts, traité 1996, dans la rel LV) → l'espace entre les deux lignes (~2 200 km²) restait blanc.
- **Correctif EE** : tools/v9ee2.js — bloc EE reconstruit depuis rel 79510 avec substitution de la ligne détaillée 993983041 (nœuds/ways de data/LV). Bloc : **1 boucle, 11 258 pts**. Golfe de Riga 100 % couvert (EE moitié NE, LV moitié SW, raccord exact même way, zéro seam) ; sondes Tallinn/Saaremaa/Hiiumaa/Ruhnu/Kihnu/Vormsi/Pärnu/Narva OK, mer ouest Saaremaa = eaux territoriales EE (fidèle OSM).
- **Correctif FI** : tools/v9fi3.js — bloc FI reconstruit depuis rel 54224 (Suomi/Finland). data/FI/nodes.json.gz (51 Mo, 5,1 M nœuds) illisible en RAM (OOM) → lecture du **nodes.npz binaire** (zip de .npy ids <i8 / lons,lats <f8, parsing direct, nœuds filtrés 19 166/19 166). Bloc : **1 boucle, 19 166 pts** (enveloppe eaux territoriales, îles incluses). Aucune perte vs ancien bloc (scan diff golfe de Finlande + Botnie : que des gains), îles Åland désormais couvertes (les enclaves blanches 22.4-23.1/60.0-60.4 disparues), golfe de Finlande EE/FI raccordés (traité EE-FI 1996), FI-RU coïncident sur les mêmes ways côté terre.
- **Aperçu (v9render.js)** : barres horizontales fausses éliminées — la « barre fine » y=721 (lat 56.054, 130 km) était un artefact de scanline dégénéré (lat du rang tombant exactement sur une trace de l'anneau LV au saillant de Daugavpils) → **remplissage à 3 sous-rangées par pixel (OR)** ; plus de liseré (rejeté : polluait l'image de preuve). v9barres : **0 barres** ; v9holes : composantes blanches 126→26, la poche n=5654 du golfe DISPARUE.
- **HTML** : régénéré **19.1 Mo, 41 pays** (FI 85 063→19 166 pts), 41 blocs gzip-base64 + 1 script viewer.
- Restants mineurs : 12 micro-enclaves blanches (n≤44, ~0.05°) autour de Vyborg/Ladoga (seam FI-RU, RU hyperknot arrondi 0.001°), Botnie médiane + golfe de Finlande médian = haute mer fidèle (comme avant), RU micro-trous connus, îles HR connues.
