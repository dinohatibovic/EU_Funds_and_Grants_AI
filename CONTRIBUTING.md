# Contributing

FinAssistBH is proprietary software. Review [LICENSE](./LICENSE) before
proposing or submitting any contribution.

External contributions require prior written agreement with the project owner.
Submitting or accepting a contribution does not grant commercial-use,
distribution, relicensing, or other rights beyond those explicitly provided
by the project license or a separate written agreement.

## Development workflow

### 1. Start from an up-to-date `main`

Do not commit directly to `main`.

```bash
git switch main
git fetch origin --prune
git pull --ff-only origin main
git status --short --branch
```

The worktree must be clean before creating a branch.

### 2. Create one branch per functional change

```bash
git switch -c feat/short-description
```

Use an appropriate branch prefix:

```text
feat/       New functionality
fix/        Bug fix
docs/       Documentation
refactor/   Internal restructuring
test/       Test-only change
chore/      Maintenance, dependencies, CI/CD, or tooling
security/   Authorized security remediation
```

Keep each branch focused on one coherent change. Do not combine unrelated
features, dependency upgrades, formatting changes, and refactors in the same
pull request.

### 3. Respect the repository architecture

Review [docs/architecture/BLUEPRINT.md](./docs/architecture/BLUEPRINT.md)
before making structural changes.

Repository responsibilities are separated intentionally:

```text
frontend/src/          Static web interface and product UI
backend/app/api/       FastAPI routes and request handling
backend/app/core/      Configuration, database, JWT, and security primitives
backend/app/services/  Backend service orchestration
ai_core/               Embeddings, ChromaDB, retrieval, reranking, and AI
data/grants.json       Structured grant source of truth
infrastructure/        Deployment, Docker, Render, and operational tooling
sdk/                   Python API client
tests/                 Backend, AI pipeline, and contract tests
```

Important boundaries:

- frontend code must not import Python modules;
- `ai_core` must not depend on FastAPI;
- API and authentication logic belong under `backend/app/`;
- AI retrieval and generation logic belong under `ai_core/`;
- deployment-specific logic belongs under `infrastructure/` or the root
  deployment configuration;
- grant records must remain structured and source-grounded.

## Required validation

Before opening a pull request, run:

```bash
make lint
make test
make ai-test
pip check
pytest -q
git diff --check
```

All relevant tests must pass. Do not hide, delete, skip, or weaken an existing
test only to make a change pass.

Also verify:

```bash
git status --short --branch
git diff --stat origin/main...HEAD
git diff --name-status origin/main...HEAD
```

The pull request must contain only the intended files.

If the repository's local pre-push gate is configured, allow it to complete
successfully before pushing. It may perform additional compile, lint, test,
shell-syntax, secret-path, and whitespace checks.

## Search, retrieval, and ranking changes

Changes affecting any of the following areas require benchmark validation:

- embeddings;
- ChromaDB ingestion or metadata;
- BM25 or dense retrieval;
- reciprocal-rank fusion;
- grant normalization;
- quality scoring;
- reranking;
- AI-answer grounding;
- relevance judgments;
- benchmark evaluation.

Such changes must include:

1. deterministic tests for the changed behavior;
2. validation of stable and unique grant identifiers;
3. validation of the search API response contract;
4. validation that result and source structures remain aligned;
5. offline evaluation against the versioned relevance judgments;
6. comparison with the current HitRate@5, MRR@10, and NDCG@10 baseline;
7. documentation of any metric regression or dataset coverage gap.

Run:

```bash
make lint
make test
make ai-test
make benchmark-test
make benchmark-syntax
```

When valid production API credentials are available, run separately:

```bash
make benchmark-run
```

A ranking change must not be accepted only because selected examples appear
better. Benchmark regressions must be documented and justified in the pull
request.

Do not invent relevance labels to improve metrics. A query without a confirmed
relevant document must remain documented as a dataset coverage gap.

## Grant data changes

Every record in `data/grants.json` must:

- have a stable and unique identifier;
- include an authoritative source URL;
- include an appropriate reliability label;
- use `null` when a deadline or another required value is not confirmed;
- distinguish an actual deadline from an informational expected date;
- avoid invented budgets, eligibility requirements, conditions, and URLs.

Follow the grant-data rules in [CLAUDE.md](./CLAUDE.md).

Changes to grant records must include relevant data-integrity and ingestion
tests.

## Dependency changes

Dependency updates must be handled separately from unrelated feature work.

For every dependency change:

1. review the package, version change, and release impact;
2. review applicable Dependabot or dependency-audit findings;
3. run `pip check`;
4. run targeted tests;
5. run the full test suite;
6. confirm that requirement files remain consistent;
7. document any temporary audit exception and its rationale.

Do not add a broad vulnerability-scan exclusion. Every exception must be
limited to an explicit advisory and reviewed when the affected dependency is
updated.

## Security requirements

Never commit:

- `.env` files;
- API keys;
- passwords;
- access tokens;
- private keys;
- database connection strings;
- production credentials;
- personal or confidential user data.

Use environment variables or approved deployment secret stores.

Do not weaken authentication, authorization, JWT validation, CORS controls,
secret handling, dependency auditing, rate limiting, or security workflows
without explicit justification and dedicated tests.

Suspected vulnerabilities must be reported privately by following
[SECURITY.md](./SECURITY.md).

Do not disclose suspected vulnerabilities through public GitHub issues,
discussions, pull requests, commit comments, or social media.

## Commit conventions

Use focused commit messages in this format:

```text
type: short description
```

Supported types include:

```text
feat
fix
refactor
docs
chore
test
security
ci
```

Examples:

```text
feat: add company profile matching contract
fix: preserve verified source ordering
docs: clarify private vulnerability reporting
chore: update backend dependencies
test: cover hybrid retrieval fallback
security: harden JWT validation
ci: validate Render deploy hook
```

Keep commits reviewable. Avoid mixing generated files, unrelated formatting,
debug output, and functional changes.

## Language conventions

- Code, identifiers, commit messages, and repository documentation are in
  English.
- User-facing product strings are primarily in Bosnian.
- Technical terms may remain in English when that improves accuracy.
- User-facing text must not claim unsupported deadlines, budgets, eligibility,
  or funding availability.

## Pull requests

Every pull request must:

- target `main`;
- contain one functional change;
- use the pull-request template;
- explain the purpose and scope;
- list the changed files or components;
- describe validation performed;
- include benchmark results when retrieval behavior changes;
- disclose dependency and security implications;
- document known limitations;
- have a clean worktree and focused diff;
- pass required local and available remote checks before merging.

Do not merge a pull request while known test failures, unresolved conflicts,
unexpected files, secrets, or unexplained benchmark regressions remain.

## Changelog requirements

Update [CHANGELOG.md](./CHANGELOG.md) under `Unreleased` for notable changes,
including:

- user-visible features;
- API contract changes;
- retrieval or benchmark changes;
- security-policy changes;
- dependency upgrades with relevant impact;
- deployment or operational changes;
- important fixes and known limitations.

Do not rewrite historical release facts unless correcting a documented error.

## Release workflow

A release may be prepared only after:

1. the intended changes have been merged into `main`;
2. local `main` matches `origin/main`;
3. the worktree is clean;
4. the version contract is updated consistently;
5. `CHANGELOG.md` is complete;
6. required tests and quality checks pass;
7. release and deployment configuration has been reviewed.

Verify:

```bash
git switch main
git fetch origin --prune
git pull --ff-only origin main

test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
git status --short --branch

make lint
make test
make ai-test
pip check
pytest -q
git diff --check
```

Create and push the annotated release tag only after validation:

```bash
git tag -a v2.3.0 -m "FinAssistBH v2.3.0"
git push origin v2.3.0
```

The release workflow is expected to create the GitHub Release and publish the
configured GHCR image.

After deployment, verify the public health endpoint and confirm that the
reported version, Git commit, database status, AI-engine status, ChromaDB
collection, and document count match the intended release.

## Reporting ordinary issues

Use the appropriate public template only for non-sensitive reports:

- Bugs: [.github/ISSUE_TEMPLATE/bug_report.md](./.github/ISSUE_TEMPLATE/bug_report.md)
- Security vulnerabilities: [SECURITY.md](./SECURITY.md)

If there is uncertainty whether a finding is security-sensitive, report it
privately.

Thank you for helping improve FinAssistBH responsibly.
