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
