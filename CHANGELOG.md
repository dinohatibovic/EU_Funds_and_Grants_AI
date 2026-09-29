# Changelog

All notable changes to the FinAssistBH platform.

The format follows [Keep a Changelog](https://keepachangelog.com/), and
versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Security

- Revised `SECURITY.md` with private vulnerability reporting guidance,
  supported-version boundaries, coordinated disclosure expectations,
  responsible testing rules, and required report details.
- Clarified that suspected vulnerabilities must not be reported through
  public GitHub issues, discussions, pull requests, commit comments, or
  social media.
- Added guidance for manually validating automated and AI-assisted security
  findings before submission.
- Added a responsible testing policy covering user data, credentials,
  production services, denial-of-service testing, and unauthorized access.
- Documented the security response process, including acknowledgement within
  72 hours and weekly updates for accepted unresolved reports.
- Documented that FinAssistBH does not currently promise a bug-bounty payment
  or other financial reward.
- Retained email as the active private reporting channel until GitHub Private
  Vulnerability Reporting is enabled for the repository.

### Changed

- Hardened the CI/CD workflow and deployment validation contract.
- Updated the project README and repository presentation.
- Updated Python dependencies across the AI and backend layers:
  - `google-genai` from `2.24.0` to `2.25.0`;
  - `uvicorn` from `0.53.0` to `0.54.0`;
  - `PyJWT` from `2.14.0` to `2.15.0`.

### Validation

- Local pre-push validation passes:
  - Ruff critical checks;
  - 24 SEDIA tests;
  - 99 AI pipeline tests;
  - 191 tests in the full suite;
  - shell syntax checks;
  - secret-path checks;
  - whitespace checks.
- Local `main` and `origin/main` were verified at the same commit after branch
  synchronization.
- Historical development branches were synchronized with the current `main`
  content without deleting remote branches.

## [2.2.1] - 2026-08-25

### Added

- Expanded the production grant dataset to 30 structured records.
- Added shared release metadata to the public health endpoint:
  `version`, `git_commit`, `chroma_collection`, and `chroma_documents`.
- Added deterministic Chroma collection and write lifecycle contract tests.
- Added automated production health verification after deployment.
- Added versioned relevance judgments and production search benchmark
  evidence for 15 representative grant queries.
- Added FastAPI lifespan behavior tests for startup ordering, database
  fallback, and failure-safe AI initialization.

### Changed

- Centralized the Gemini embedding model contract.
- Standardized Gemini embeddings at 3072 dimensions.
- Centralized the ChromaDB collection contract as `eu_grants`.
- Unified structured metadata and embedding text generation across primary
  grant ingestion paths.
- Migrated FastAPI startup initialization from the deprecated
  `@app.on_event("startup")` mechanism to the lifespan context manager.
- Updated the application version contract to `2.2.1`.
- Improved quality-aware reranking for grant search results.

### Fixed

- Made production ChromaDB dataset synchronization failure-safe by upserting
  the new dataset before deleting stale records.
- Prevented failed embedding or upsert operations from deleting the existing
  production collection.
- Removed the FastAPI `on_event` deprecation warning.
- Preserved database fallback, grant cache loading, AI client initialization,
  and ChromaDB auto-ingestion during the lifespan migration.

### Production Validation

- Production release commit:
  `f8355363ef9ea16ce8fd4a376c57fd6144511c33`.
- Public health endpoint reports version `2.2.1` and the matching Git commit.
- PostgreSQL connection reports `connected`.
- AI engine reports `ready`.
- ChromaDB collection `eu_grants` reports 30 documents.
- Three Gemini embedding batches of 10 records completed successfully.
- Embedding vectors use 3072 dimensions.
- Full automated test suite: 87 passing tests.
- GitHub Release and GHCR image published with tags `2.2.1` and `latest`.

### Search Benchmark

Full 15-query production baseline:

- HitRate@5: `0.8667`
- MRR@10: `0.7622`
- NDCG@10: `0.6293`

Fourteen evaluable queries, excluding one documented dataset coverage gap:

- HitRate@5: `0.9286`
- MRR@10: `0.8167`
- NDCG@10: `0.6573`

Production processing time across 15 search requests:

- Mean: `0.2423` seconds
- Median: `0.2421` seconds
- Minimum: `0.2171` seconds
- Maximum: `0.2699` seconds
- P95 nearest rank: `0.2699` seconds

### Known Limitations

- The benchmark query `zapošljavanje mladih u FBiH` is recorded as a dataset
  coverage gap because the current judgment set has no document with binary
  relevance grade `>= 2`.
- The Render free instance can sleep during inactivity, so the first request
  after an idle period can have substantially higher latency.

## [2.2.0] - 2026-07-19

### Added

- Added the enterprise layered repository structure:
  - `ai_core/` for the AI layer;
  - `backend/app/` for API, core, and services;
  - `frontend/src/`;
  - `infrastructure/`;
  - `docs/`.
- Added the GitHub Actions CI/CD pipeline covering linting, tests, Render
  deployment, and GitHub Pages deployment.
- Added the security audit workflow with weekly and push-triggered
  `pip-audit`, Bandit, and gitleaks checks.
- Added a release workflow that creates a GitHub Release and publishes the
  Docker image to GHCR from a version tag.
- Added Docker Compose for local development.
- Added optional Kubernetes manifests.
- Added Makefile commands for development, testing, linting, ingestion, and
  local orchestration.
- Added Dependabot, issue and pull-request templates, funding configuration,
  contribution guidance, and onboarding documentation.
- Added the architecture blueprint and dependency matrix under
  `docs/architecture/BLUEPRINT.md`.
- Added GDPR and EU AI Act documentation under `docs/regulatory/`.
- Expanded the automated suite to 31 backend, AI pipeline, and data-integrity
  tests.

### Changed

- Changed the application entry point from `uvicorn main:app` to
  `uvicorn backend.app.main:app`.
- Made the ChromaDB path configurable through `CHROMA_DB_PATH`.
- Updated `data/grants.json` so unverified entries are explicitly labeled and
  expired deadlines use `null`.

### Fixed

- Updated `sdk/client.py` so JWT-protected `/search` requests use `login()` and
  the `Authorization` header.
- Updated `web_scraper.py` so missing deadlines fall back to an empty string
  because ChromaDB metadata does not accept `None`.
- Added a timeout to HTTP calls in `api_loader.py`.
- Annotated Bandit B608 false positives for parameterized queries.
- Removed duplicate and incorrect entries from `.gitignore`.

## [2.1.0] - 2026-06

### Added

- Added the `/ai-answer` endpoint with RAG and Gemini generation in Bosnian
  and English.
- Added the `/grants`, `/grants/local`, and `/grants/urgent` REST endpoints.
- Added rate limiting of 30 requests per 60 seconds per IP.
- Added email validation and JWT authentication.
- Added graceful PostgreSQL-to-SQLite database fallback during startup.
- Added the production CORS allowlist.

## [2.0.0] - 2026-03

### Added

- Released the first production version based on FastAPI, ChromaDB, Gemini
  embeddings, and retrieval-augmented generation.
- Added the frontend chat, authentication, and investor pitch interfaces on
  GitHub Pages.
- Added Render deployment with automatic grant ingestion during startup.
  
