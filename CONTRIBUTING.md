# Contributing

> ⚠️ FinAssistBH is proprietary software (see [LICENSE](./LICENSE)) — external
> contributions are only possible by prior agreement with the owner.

## Workflow

1. **One branch per change** — never commit directly to `main`:
   ```bash
   git checkout -b feat/short-description   # or fix/, docs/, chore/
   ```
2. **Development** — follow the existing layer structure (see
   [docs/architecture/BLUEPRINT.md](./docs/architecture/BLUEPRINT.md)):
   API logic goes in `backend/app/api/`, AI logic in `ai_core/`, never the
   other way around.
3. **Before opening a PR**, always run:
   ```bash
   make lint      # ruff — critical errors
   make test      # backend tests
   make ai-test   # AI pipeline tests
   ```
4. **PR to `main`** — fill in the template; CI must be green before merging.
5. **Release** — after merging significant changes: update `CHANGELOG.md`,
   bump the version and push a tag:
   ```bash
   git tag -a v2.3.0 -m "FinAssistBH v2.3.0" && git push origin v2.3.0
   ```
   The Release workflow automatically creates a GitHub Release and publishes
   the GHCR Docker image.

## Conventions

- **Commit messages:** `type: short description` (feat/fix/refactor/docs/chore/test)
- **Language:** code and identifiers in English; user-facing product strings
  in Bosnian (the product language); repository documentation in English
- **Secrets:** environment variables only — never in code or commits
- **Grant data:** every entry in `data/grants.json` must have a source (URL)
  and a reliability label; deadlines not confirmed by a source → `null`
  (rules in [CLAUDE.md](./CLAUDE.md))

## Reporting issues

- Bugs: [issue template](./.github/ISSUE_TEMPLATE/bug_report.md)
- Security: [SECURITY.md](./SECURITY.md) — critical issues privately, never publicly!
