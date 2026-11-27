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

## 26/11 nuit 2 — Russie européenne (limite Europe/Asie physique)

- **Diagnostic** : le bloc RU était découpé au méridien CUT=41.55 et surtout ne contenait que 43 sujets OUEST de la Russie (manquaient : Perm, Komi, Kirov, Oudmourtie, Bachkirie, Tatarstan, Samara, Saratov, Astrakhan, Orenbourg, Sverdlovsk, Tcheliabinsk, Kourgan) → les « régions/isolats » vus par l'utilisateur. 13 sujets récupérés depuis hyperknot/country-levels-export (geojson/high/iso2/RU/RU-XX.geojson, Kourgan = **RU-KGN** pas RU-KU/KUR).
- **Abandon de la dissolution globale** : hyperknot simplifie chaque sujet indépendamment → frontières internes non exactement superposables ; l'annulation d'arêtes + filtre raster + élagage pendantes + rechaînage (essais dirigé PUIS non-dirigé) fragmentait le continent (597-1302 micro-faces, sondes AUCUNE). Le face-walk dirigé se bloque sur les nœuds à déséquilibre d'orientation (2 entrantes / 0 sortante) laissés par la dissolution.
- **Solution (v9ru2.js réécrit)** : clip Europe **par sujet** (Weiler-Atherton contre EP = polyligne Oural→fleuve Oural→Caspienne + fermeture), orientation normalisée par sujet (outre CCW, trous CW), 56 sujets → 1 038 anneaux, filtre polaire (>71° merc : FJ/Nouvelle-Zemble droppés), toutes les boucles clippées alimentent le bloc RU. Bloc : **808 boucles, 156 464 pts**, bbox 19.80/45.29/66.25/102.17.
- **Contour blanc** : les frontières internes entre sujets ne doivent pas être tracées en blanc → drapeau `noc:1` dans le bloc RU, v9html saute le path de contour pour RU (les voisins dessinent leur propre liseré, RU/mer = contraste gris/fond).
- **Validation** : sondes IN (Moscou, StP, Perm, Samara, Astrakhan, Grozny, Syktyvkar, Mourmansk, Arkhangelsk, Krasnodar, Oufa, Kazan, Saratov, Kaliningrad) ; OUT (Iekaterinbourg, Tcheliabinsk, Magnitogorsk, Orenbourg-est, Novossibirsk, Salekhard). Zoom Oural : bord est continu et lisse. Composantes blanches fermées : 3 mers (Noire/Caspienne/Azov) + Volga-Volgograd 271 km², tundra Vorkuta 229 km², fleuves/lacs ≤104 km².
- **Restant connu** : bande côtière de Sotchi (~40×20 km) absente — défaut du geojson RU-KDA (w=0 même en nonzero, côte coupée) ; déjà absente de l'ancien bloc rel 60189. RU-FI : micro-enclaves Vyborg/Ladoga inchangées.

## 26/11 nuit 3 — Russie : niveau pays UNIQUE (dissolution par trame)

- **Demande** : plus aucune région/sujet affiché sur la carte Russie. Cause : le HTML trace 1 <path> par boucle, le bloc RU en avait 808 (une par morceau de sujet) → coutures visibles.
- **Solution (tools/v9ru3.js)** : dissolution PAYS par trame — rasterisation nonzero 0.002° (~346 Mcellules, Uint8Array, --max-old-space-size=6000), extraction des arêtes de bord (terre à gauche), chaînage par tri des K1 + lowerBound, fermeture sur l'arête de départ, aires shoelace (extérieurs CCW ≥0.3 km², trous CW ≥350 km² pour boucher les fentes inter-sujets), Douglas-Peucker 0.0025 merc, sortie ps 5 décimales.
- **Sujets manquants découverts** : RU-ULY (Oulianovsk), RU-NGR (Novgorod), RU-TUL (Toula) n'étaient PAS dans data/RU-hk (manquaient depuis le début) → 3 trous géants. Téléchargés via tools.github_app.get_file_contents + tools.file_system.write_file (47 453/47 536/39 518 octets). data/RU-hk = 59 sujets.
- **Résultat** : v9ru2 → 812 boucles/163 807 pts (59 sujets, clip Europe inchangé) ; v9ru3 → **continent unique 3 693 527 km² + 268 îles = 269 boucles, 50 179 pts, 0 trou gardé**. Le drapeau noc devient inutile (contour blanc normal, comme les autres pays).
- **Bugs corrigés dans v9ru3** : (a) winding w remis à zéro par groupe au lieu de persister sur la ligne (perdait la moitié du terrain) ; (b) fermeture prématurée au sommet de départ (continent fragmenté) → fermer sur l'ARÊTE de départ (next===e0 autorisé) ; (c) pip des trous comparait lat vs mercator.
- **Validation** : sondes IN 19/19 (Moscou, StP, Perm, Samara, Astrakhan, Grozny, Oulianovsk, Novgorod, Toula, Mourmansk, Arkhangelsk, Krasnodar, Oufa, Kazan, Saratov, Kaliningrad, Syktyvkar, Voronej, Rostov) ; OUT OK (Iekaterinbourg, Tcheliabinsk, Novossibirsk, Salekhard) ; vision : aucune frontière interne, bord Oural continu au zoom. Limites : segment Orsk→Orenbourg droit vs fleuve méandreux (~50 km près d'Orenbourg), Sotchi absent (défaut RU-KDA inchangé), trame 0.002° ≈ 200 m de lissage.
- **HTML** : régénéré 19.1 Mo, 41 pays (RU 269 boucles). Sondes via tools/v9probe-ru.js (pip flat, i+=2).

## 27/11 — Régions Russie : hors affichage, conservées au package

- **Affichage** : le bloc RU (blocs/RU.json.gz, 269 boucles) ne contient que le niveau pays — AUCUNE région affichée (validé nuit 3 : sondes 19/19, vision sans frontières internes). Si des régions sont visibles, c'est l'ANCIEN fichier HTML (808 boucles) : re-télécharger europe-v10-test.html.
- **Package** : prisme-v10/regions/RU.regions.json.gz = bloc pré-dissolution (812 boucles, 163 807 pts, sujets individuels) conservé comme les autres pays à régions (DE/EE/PL/UA). Données régionales donc intactes, simplement non dessinées.
- **GitHub** : commit 1228346 (RU.regions.json.gz.b64 1 056 737 car, 353 lignes, push vérifié longueur exacte). Zip prisme-v10-complet.zip reconstruit avec regions/RU.regions.json.gz.

## 27/11 — Norvège : côte ouest simplifiée 25%, îles extrême nord supprimées

- **Demande** : côte ouest de la NORVÈGE trop détaillée → simplifier ~25% ; supprimer les îles à l'extrême nord du tracé et du package.
- **v9no2.js** : (1) 28 anneaux îles latmin > 71.5° (Svalbard + Bjørnøya/Hopen/Kong Karls) supprimés, 29 619 pts ; (2) côte ouest (zone lon < 17.5, frontières FI/RU non touchées) simplifiée par Douglas-Peucker calibré par dichotomie : tolérance 0.00096° merc, **43 401 pts retirés = 25.0% exactement**. Jan Mayen (lon −9) retiré ensuite (anneau lon < 0). Bloc : 305 → 276 boucles, 256 654 → 183 329 pts (pts champ inchangé par endroits, recalculé). Backup : out/backup/NO-pre-no2.json.gz.
- **Validation** : rendu apercu-norvege-41.png + zoom Finnmark (vision : plus d'île détachée au nord, côte ouest continue Stavanger→cap Nord) ; sondes identiques avant/après (les 5 FAIL préexistantes = sondes en bordure de fjord à cette précision, pas des régressions) ; Longyearbyen/Jan Mayen/Féroé exclus.
- **HTML** : régénéré 18.4 Mo, 41 pays, bbox top 103.00 (cap Nord désormais pointe nord de la carte).
- **Package** : prisme-v10/blocs/NO.json.gz remplacé (îles extrême nord absentes du package, comme demandé) ; GitHub commit 40000ce (NO.json.gz.b64 1 492 742 car vérifié).
- **Piège** : pip sur blocs NON fermés (anneaux sans répétition du 1er point) → fermer q.push(q[0],q[1]) avant test ; run_typescript limite 16 Mo → ne pas accumuler > ~25 résultats d'opérations (le push a réussi malgré le MemoryLimitError affiché après).

## 27/11 (2) — Grèce : 20% des plus petites îles supprimées ; Chypre : zone maritime retirée

- **Demande** : supprimer les 20% des îles grecques les plus petites ; Chypre : la carte montrait sa zone maritime (erreur : on n'affiche pas les limites des zones maritimes) ; division Chypre en 2 (côté grec / côté turc) À INTÉGRER DANS LA PROCHAINE VERSION (v11).
- **GR (tools/v9gr.js)** : 59 îles (hors continent) triées par aire shoelace corrigée latitude ; 12 plus petites supprimées (17-147 km² : Psara, Nisyros, Anafi, Folegandros, etc.) → 61→49 boucles, 54 328→50 287 pts. Backup out/backup/GR-pre-iles20.json.gz.
- **CY** : le ps 0 (517 pts, lat jusqu'à 35,91°N, lon 32,02°O, 5,3 deg²) était la zone maritime (revendication EEZ/eaux territoriales) → supprimé ; reste l'île réelle (ps 5, 26 007 pts) + 4 fragments littoraux Larnaca. 6→5 boucles. Backup out/backup/CY-pre-maritime.json.gz.
- **Validation** : sondes 20/21 OK (Rhodes : sonde préexistante en rade, identique avant/après) ; vision : Chypre = île simple entourée de mer, Crète/Rhodes intactes.
- **v11 TODO** : Chypre divisée en 2 (République de Chypre / Chypre du Nord) — frontière OSM ligne verte (relation Northern Cyprus), à récupérer depuis hyperknot ou OSM ; deux blocs CY + CY-TR (ou multi-boucles avec trou frontalier).
- **Publications** : HTML 18.4 Mo régénéré, apercu-grece-41.png, prisme-v10/blocs GR+CY remplacés, GitHub 0349ef4 (GR+CY b64), zip reconstruit.

## 27/11 (3) — Finlande côte ouest détaillée, Russie micro-îles supprimées, Islande redimensionnée

- **FI (tools/v9fi4.js)** : la « côte ouest » affichée était l'enveloppe des eaux territoriales (lisse, segments 2,5 km). Substitution : section ouest de l'enveloppe remplacée par la vraie côte détaillée du backup coastvec (FI-pre-rel54224), zone lat 60.0-64.3 (Porkkala→Oulu), 29 677 pts à segments 128 m (au lieu de 277 pts), + 110 îles d'archipel (incl. Åland) reprises du bloc détaillé. Bande de fausse mer eaux territoriales (12 MN) retirée → mer blanche entre côte et ancienne enveloppe. 2 jonctions droites en mer (Porkkala ~200 m, Oulu ~30 km). Bloc : 111 boucles, 82 812 pts. Backup FI-pre-fi4.json.gz. Sondes OK (Hanko/Porkkala/Helsinki/Turku/Pori/Vaasa/Mariehamn TERRE, bandes mer → mer) ; zoom Vaasa vision : côte et archipel très détaillés.
- **RU (tools/v9ru4-is.js)** : 216 micro-îles < 5 km² supprimées (3 056 pts) ; 52 îles conservées (Solovetsky etc.) + continent = 53 boucles, 47 123 pts. Backup RU-pre-microiles.json.gz. PIÈGE : aire shoelace FAUSSÉE si anneau non fermé (fermer avec le 1er point avant shoelace) — les îles semblaient ≥135 km².
- **IS (même script)** : redimensionnée ×0,78 en mercator autour du centre bbox (aire apparente ÷1,64) — compensation de l'inflation Mercator à 65°N (facteur sec²≈5,6) vs îles britanniques (~57°N, sec²≈3,4), pour une taille apparente proportionnelle. Île sans voisin terrestre → aucun risque de couture. Backup IS-pre-resize.json.gz.
- **HTML** : régénéré 18,8 Mo, 41 pays. Rendus : apercu-finlande-41, apercu-vaasa-zoom, apercu-islande-41, apercu-russie-41 (vision : Islande intacte, côtes russes nettoyées).
- **GitHub** : c5f4276 (RU), 6db1ad2 (FI), 5758c6a (IS, 1 593 519 car vérifiés). Package prisme-v10/blocs mis à jour, zip reconstruit.

## 27/11 (4) — Micro-îles < 5 km² supprimées (tous pays)

- **Demande** : supprimer tous pays confondus les îles de moins de 5 km², avec compte rendu du nombre supprimé.
- **Passe 1 annulée** : v9micro.js v1, parseur cassé sur le format SVG « L x y » espacé (FR/HR) → NaN → aires garbage → restauration depuis out/backup/*-pre-microiles.json.gz.
- **v9micro2.js (3 passes par pays, robustes)** : scan (boucles < 5 km², shoelace anneau fermé, conversion ylat AVANT l'aire), cover (centroïde vs grandes boucles de TOUS les pays, pip Float32Array décimé ×4 anneau fermé), drop (îles = non couvertes ; enclaves et îles de lacs = couvertes donc conservées). Backups *-pre-microiles-v2.json.gz.
- **Résultat : 2 544 îles supprimées, 149 658 points retirés** — DK 860, IE 942, PT 535, IS 125, HR 51, FI 29, FR 2. Enclaves intactes : Baarle-Hertog (BE 21), Baarle-Nassau (NL), Venn (DE 5), Brčko (BA 1), fragments Llívia (FR). UA 2 et CY 4 couvertes, conservées. RU déjà nettoyé (216 îles la veille).
- **Blocs** : DK 900→40 boucles, IE 958→16, PT 549→14, IS 127→2, FI 111→82, HR 106→55, FR 17→15. Sondes capitales OK.
- **HTML** : 17,86 Mo, 41 pays, régénéré. GitHub : DK/IE/PT/IS/FI/HR/FR .json.gz.b64 poussés (tailles vérifiées : DK 1 712 462, IE 1 903 430, IS 1 465 420).
- **TODO v11** : Chypre divisée grec/turc (ligne verte OSM).

## 27/11 (5) — Frontières Andorre et Liechtenstein supprimées

- Andorre : aucune frontière tracée (anneau annexé FR boucle 11 exclu du contour via champ `noci=[11]`, remplissage conservé). Liechtenstein : liseré supprimé (CH boucle 1, `noci=[1]`) → territoire fusionné visuellement avec la Suisse ; frontière LI/AT toujours dessinée par l'Autriche. v9annexe.js + filtre noci dans v9html.js. Backups FR/CH-pre-annexe. Commit bcd33ce (FR 172 765 / CH 375 201 car vérifiés). HTML 17,86 Mo.

## 27/11 (6) — LOD 3 niveaux par pays

- v9lod.js : L1 monde (DP 0.03°, îles ≥400 km²), L2 continent (DP 0.008°, îles ≥25 km²), L3 = final. Micro-états protégés. noci propagé.
- v9lodhtml.js : europe-v10-lod.html 18,7 Mo — L1 instantané, L2/L3 préchargés invisiblement, bascule auto L2 < 33 % de la vue monde, L3 < 10 %. Sondes 3 niveaux OK.
- Package : prisme-v10/blocs-lod/ (41 blocs {iso,nom,L[3]}), zip 56,2 Mo.

## 27/11 (7) — Correctif viewer LOD (blocage « Chargement… »)

- Cause : ids des script tags = index global d'embed (b0_0, b1_1, b2_2, b0_3…) au lieu de b{lvl}_{index-pays} → getElementById null → exception silencieuse.
- Correctif v9lodhtml.js : ids b{lvl}_{ci}, data-iso, try/catch visible (« ERREUR: msg »). HTML régénéré.
- Validation : simulation chargement viewer (gunzipBlock exact, 123 tags) : OK=123 FAIL=0. Règle : simuler avant de livrer tout HTML.
