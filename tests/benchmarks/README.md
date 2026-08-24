# FinAssistBH Search Benchmark Suite

Benchmark alat provjerava kvalitet produkcijskog endpointa `/search` kroz skup reprezentativnih upita za BiH, FBiH, ZDK i Tešanj.

## Obuhvaćene teme

- digitalizacija MSP
- proizvodnja i CNC
- startupi i AI
- poljoprivreda
- obrti
- zapošljavanje
- energetska efikasnost
- izvoz i konkurentnost

## Preduvjeti

- `curl`
- `jq`
- valjan FinAssistBH aplikacijski JWT
- mrežni pristup produkcijskom API-ju

## Pokretanje

```bash
bash tests/benchmarks/run_search_benchmark.sh
```

Skripta traži JWT kroz skriveni terminalski unos. JWT se ne zapisuje u izlazne datoteke.

Radi smanjenja rizika od zapisivanja tokena u shell historiju, preporučuje se skriveni interaktivni unos. Ne zapisivati JWT u `.env`, skriptu, dokumentaciju ili Git.

## Rezultati

Svako pokretanje kreira vremenski označen direktorij:

```text
tests/benchmarks/results/YYYY_MM_DD_HHMMSS/
```

Rezultati uključuju:

- pojedinačne JSON odgovore
- `SUMMARY.md`
- naslove rangiranih grantova
- vrijeme obrade kada ga API vrati

Direktorij `tests/benchmarks/results/` ignoriran je u Gitu.

## Ograničenja

Ova skripta prikuplja rezultate, ali ne računa automatski metrike kvalitete kao što su Precision@K, Recall@K, MRR ili NDCG. Rezultate je potrebno ručno pregledati ili naknadno evaluirati prema očekivanim relevantnim grantovima.
