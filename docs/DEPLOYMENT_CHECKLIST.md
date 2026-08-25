# FinAssistBH Deployment Checklist

## 1. Repository state

- [ ] Worktree is clean.
- [ ] Active branch is expected.
- [ ] Local branch is synchronized with `origin`.
- [ ] Pull request checks are green.
- [ ] No credentials or `.env` content are staged.
- [ ] `git diff --check` passes.

## 2. Required production configuration

- [ ] `GEMINI_API_KEY` is configured.
- [ ] `JWT_SECRET` is stable and configured outside the repository.
- [ ] `DATABASE_URL` points to the production PostgreSQL database.
- [ ] `WEB_CONCURRENCY=1` is retained while using process-local state.
- [ ] Python runtime settings match the deployed application.
- [ ] The Render start command launches `backend.app.main:app`.

## 3. Application contracts

- [ ] FastAPI uses the lifespan context manager.
- [ ] The deprecated FastAPI startup event handler remains removed.
- [ ] Embedding model is `gemini-embedding-001`.
- [ ] Embedding vectors use 3072 dimensions.
- [ ] Chroma collection is `eu_grants`.
- [ ] The source dataset contains 30 unique grant records.
- [ ] Chroma synchronization is failure-safe.
- [ ] Database fallback behavior is tested.

## 4. Local quality gate

Run:

```bash
python -m pytest -q
python -m pip check
git diff --check
```

Expected verified baseline:

```text
87 tests passed
No broken requirements found
```

## 5. Post-deployment health verification

Check:

```bash
curl -fsS \
  --max-time 90 \
  https://eu-funds-and-grants-ai.onrender.com/health
```

Verify:

```text
status=healthy
version=2.2.1
git_commit=<deployed main commit>
chroma_collection=eu_grants
chroma_documents=30
database=connected
db_type=postgresql
ai_engine=ready
grants_total=30
grants_in_vector_db=30
```

The Render free instance can require 50 seconds or more to wake after
inactivity.

## 6. Authenticated user-flow smoke test

- [ ] Registration returns HTTP 200.
- [ ] Login or registration returns a JWT.
- [ ] `/auth/me` confirms the authenticated identity.
- [ ] `/search` without JWT returns HTTP 401.
- [ ] `/ai-answer` without JWT returns HTTP 401.
- [ ] Authenticated `/search` returns HTTP 200.
- [ ] Search response includes results, documents, metadata, request ID, and
  processing time.
- [ ] Authenticated `/ai-answer` returns HTTP 200.
- [ ] AI answer includes non-empty answer text, sources, request ID, and
  processing time.
- [ ] Temporary credentials and token artifacts are deleted.

## 7. Production benchmark

- [ ] Run all 15 benchmark queries.
- [ ] Confirm 15 JSON result files.
- [ ] Confirm every result contains `grant_id` metadata.
- [ ] Run the deterministic evaluator.
- [ ] Store full 15-query metrics.
- [ ] Store the 14-query evaluable sensitivity metrics.
- [ ] Review Query 13 as a dataset coverage gap.
- [ ] Review Query 14 as a ranking failure.

Verified v2.2.1 baseline:

```text
Full HitRate@5:      0.8667
Full MRR@10:         0.7622
Full NDCG@10:        0.6293

Evaluable HitRate@5: 0.9286
Evaluable MRR@10:    0.8167
Evaluable NDCG@10:   0.6573
```

## 8. Release and container verification

- [ ] Create an annotated release tag.
- [ ] Confirm the tag points to the intended release commit.
- [ ] Confirm GitHub Release is published.
- [ ] Confirm release is not a draft.
- [ ] Confirm release is not a prerelease.
- [ ] Confirm the GHCR version tag exists.
- [ ] Confirm the GHCR `latest` tag exists.
- [ ] Confirm both tags resolve to the expected manifest.
- [ ] Record the immutable container digest.

Verified v2.2.1 artifact:

```text
Release commit:
f8355363ef9ea16ce8fd4a376c57fd6144511c33

Container:
ghcr.io/dinohatibovic/finassistbh-backend:2.2.1

Immutable manifest:
ghcr.io/dinohatibovic/finassistbh-backend@sha256:7878f5e101107423fedc37643461d7b34e5818ea7ab5737dff8c0020319a62e1
```

## 9. Final consistency

- [ ] Production health reports the expected deployed commit.
- [ ] Local `main` equals `origin/main`.
- [ ] Worktree is clean.
- [ ] Release tag has not been moved.
- [ ] Documentation distinguishes the release commit from later
  post-release documentation commits.
