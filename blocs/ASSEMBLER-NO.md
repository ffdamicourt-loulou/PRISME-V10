# Bloc Norvege (NO.json.gz) - reassemblage

Le bloc final NO (simplifie 75%, 305 boucles, 256 654 pts) est stocke en 4 parts base64.

Reassembler:
```bash
cat blocs/NO.json.gz.part1.b64 blocs/NO.json.gz.part2.b64 blocs/NO.json.gz.part3.b64 blocs/NO.json.gz.part4.b64 | tr -d '\n' | base64 -d > NO.json.gz
gzip -t NO.json.gz && echo OK
```
Taille attendue: 1 620 944 octets.
