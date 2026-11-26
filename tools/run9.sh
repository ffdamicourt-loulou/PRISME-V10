#!/bin/bash
# v9 run9.sh <ISO> <geofabrik-slug> <n1levels> [annexISO...]
# télécharge, extrait (niveaux 2,4,6), construit la silhouette id-OSM, publie.
set -e
ISO="$1"; SLUG="$2"; N1="$3"; shift 3
ANNEX="$*"
W=${W9_ROOT:-/tmp/w9}/$ISO
mkdir -p $W
cd $W
mkdir -p out1
if [ ! -f $W/$ISO.osm.pbf ]; then
  bash /home/user/artifacts/v9/tools/dl.sh "https://download.geofabrik.de/europe/$SLUG/$SLUG-latest.osm.pbf" $W/$ISO.osm.pbf 48
fi
cd $W
E=/home/user/artifacts/v9/tools/extract.js
[ -f out1/rels.json ] || node $E $ISO.osm.pbf out1 2,4,6 1
[ -f out1/ways.json ] || node $E $ISO.osm.pbf out1 2,4,6 2
[ -f out1/nodes.json ] || node $E $ISO.osm.pbf out1 2,4,6 3
node /home/user/artifacts/v9/tools/v9ring.js out1 $ISO "$N1" $ANNEX
D=/home/user/artifacts/v9/data/$ISO
mkdir -p $D
cp out1/land9.json.gz $D/
gzip -c out1/ways.json > $D/ways.json.gz
gzip -c out1/nodes.json > $D/nodes.json.gz
gzip -c out1/rels.json > $D/rels.json.gz
echo "PUBLIÉ $ISO"