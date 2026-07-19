# Doprinošenje projektu

> ⚠️ FinAssistBH je vlasnički softver (vidi [LICENSE](./LICENSE)) — vanjski
> doprinosi su mogući samo uz prethodni dogovor s vlasnikom.

## Workflow

1. **Grana po izmjeni** — nikad direktno na `main`:
   ```bash
   git checkout -b feat/kratki-opis   # ili fix/, docs/, chore/
   ```
2. **Razvoj** — prati postojeću strukturu slojeva (vidi
   [docs/architecture/BLUEPRINT.md](./docs/architecture/BLUEPRINT.md)):
   API logika u `backend/app/api/`, AI logika u `ai_core/`, nikad obrnuto.
3. **Prije PR-a** obavezno:
   ```bash
   make lint      # ruff — kritične greške
   make test      # backend testovi
   make ai-test   # AI pipeline testovi
   ```
4. **PR prema `main`** — popuni šablon; CI mora biti zelen prije merge-a.
5. **Release** — nakon merge-a značajnih izmjena: ažuriraj `CHANGELOG.md`,
   podigni verziju i pušaj tag:
   ```bash
   git tag -a v2.3.0 -m "FinAssistBH v2.3.0" && git push origin v2.3.0
   ```
   Release workflow automatski kreira GitHub Release + GHCR Docker image.

## Konvencije

- **Commit poruke:** `tip: kratki opis` (feat/fix/refactor/docs/chore/test)
- **Jezik:** kod i identifikatori engleski; komentari, docstringi i
  user-facing poruke bosanski
- **Tajne:** isključivo env varijable — nikad u kodu ili commitima
- **Podaci o grantovima:** svaki unos u `data/grants.json` mora imati izvor
  (URL) i oznaku pouzdanosti; rokovi bez potvrde iz izvora → `null`
  (pravila u [CLAUDE.md](./CLAUDE.md))

## Prijava problema

- Bug: [issue šablon](./.github/ISSUE_TEMPLATE/bug_report.md)
- Sigurnost: [SECURITY.md](./SECURITY.md) — kritično privatno, ne javno!
