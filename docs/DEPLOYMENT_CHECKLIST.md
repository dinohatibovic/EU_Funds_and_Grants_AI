# Deployment Checklist

## Pre-deployment
- [ ] Python version 3.12+
- [ ] Virtual environment activated
- [ ] All packages installed (`pip install -r requirements.txt`)
- [ ] `.env` file with the API key
- [ ] ChromaDB initialized (startup auto-ingest or `make ingest`)
- [ ] All tests green (`make test`, `make ai-test`)

## API checks
- [ ] EmbeddingClient works
- [ ] GenAIClient works (`GEMINI_MODEL` valid)
- [ ] ChromaDB search works
- [ ] No hardcoded keys

## Git checks
- [ ] All files committed
- [ ] `.env` in `.gitignore`
- [ ] No merge conflicts
- [ ] Remote configured

## Render (production)
- [ ] Start Command: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
- [ ] Env variables set: `GEMINI_API_KEY`, `JWT_SECRET`
- [ ] Health check path: `/health`
- [ ] GitHub connection active (deploys not failing with clone 403)

## Security
- [ ] API key not in code
- [ ] `.env` not in git
- [ ] No sensitive data
- [ ] Security Audit workflow green

## Documentation
- [ ] README.md up to date
- [ ] CHANGELOG.md entry for the release
- [ ] Docstrings present
