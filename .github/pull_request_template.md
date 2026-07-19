# Opis izmjene

<!-- Šta i zašto? Ako postoji povezani issue, referenciraj ga: Closes #XX -->

## Tip izmjene

- [ ] 🐛 Bug fix
- [ ] ✨ Nova funkcionalnost
- [ ] ♻️ Refactor (bez promjene ponašanja)
- [ ] 📝 Dokumentacija
- [ ] 🔒 Sigurnost
- [ ] 🏗️ Infrastruktura / CI

## Pogođeni sloj

- [ ] `ai_core/` (AI/RAG)
- [ ] `backend/` (API)
- [ ] `frontend/`
- [ ] `infrastructure/` / `.github/`
- [ ] `docs/` / `data/`

## Checklist

- [ ] Testovi prolaze lokalno (`make test` i `make ai-test`)
- [ ] Lint prolazi (`make lint`)
- [ ] Nema tajni/ključeva u kodu
- [ ] CHANGELOG.md ažuriran (ako je user-facing izmjena)
