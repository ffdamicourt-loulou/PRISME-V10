#!/bin/bash
# ring9.sh <ISO> <n1CSV> [annexISO...] — refait uniquement v9ring + publication
set -e
ISO="$1"; N1="$2"; shift 2
cd /tmp/w9/$ISO
node /home/user/artifacts/v9/tools/v9ring.js out1 $ISO "$N1" "$@" 2>&1 | grep -v "NON FERM"
D=/home/user/artifacts/v9/data/$ISO
mkdir -p $D
cp out1/land9.json.gz $D/
gzip -c out1/ways.json > $D/ways.json.gz
gzip -c out1/nodes.json > $D/nodes.json.gz
gzip -c out1/rels.json > $D/rels.json.gz
echo "PUBLIÉ $ISO"