# Deployment Checklist

## Pre-Deployment
- [ ] Python verzija 3.10+
- [ ] Virtual environment aktiviran
- [ ] Svi paketi instalirani
- [ ] .env datoteka sa API ključem
- [ ] ChromaDB baza inicijalizirana
- [ ] Ingestion proces uspio
- [ ] Sve testove prošle

## API Provjera
- [ ] EmbeddingClient radi
- [ ] GenAIClient radi
- [ ] ChromaDB pretraga radi
- [ ] Nema hardkodiranih ključeva

## Git Provjera
- [ ] Sve datoteke komitovane
- [ ] .env u .gitignore
- [ ] Nema merge konflikata
- [ ] Remote je postavljen

## Sigurnost
- [ ] API ključ nije u kodu
- [ ] .env nije u git-u
- [ ] Nema osjetljivih podataka
- [ ] Permisije su ispravne

## Dokumentacija
- [ ] README.md ažuriran
- [ ] Komentari u kodu
- [ ] Docstrings su prisutni
- [ ] Primjeri su dostupni
