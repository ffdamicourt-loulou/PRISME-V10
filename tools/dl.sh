#!/bin/bash
# v8 dl — telecharge segmente parallele + verif md5
#   dl.sh <url> <sortie> <nseg>
set -e
URL="$1"; OUT="$2"; N="${3:-64}"
D=$(mktemp -d)
LEN=$(curl -sIL "$URL" | grep -i '^content-length:' | tail -1 | tr -dc '0-9')
echo "taille: $LEN octets ($((LEN/1024/1024)) MiB)"
SEG=$(( (LEN + N - 1) / N ))
for i in $(seq 0 $((N-1))); do
  S=$((i*SEG)); E=$((S+SEG-1)); [ $E -ge $LEN ] && E=$((LEN-1))
  [ $S -ge $LEN ] && break
  curl -sL --retry 5 -r $S-$E -o "$D/part_$i" "$URL" &
done
wait
cat $(ls -v $D/part_* | sort -t_ -k2 -n) > "$OUT"
rm -rf "$D"
MD5=$(md5sum "$OUT" | cut -d' ' -f1)
echo "md5 local : $MD5"
EXP=$(curl -sL "$URL.md5" | cut -d' ' -f1)
echo "md5 remote: $EXP"
[ "$MD5" = "$EXP" ] && echo "MD5 OK" || { echo "MD5 ECHEC"; exit 1; }