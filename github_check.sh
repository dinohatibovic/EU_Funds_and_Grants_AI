#!/bin/bash
echo "=== GIT VERSION ==="
git --version

echo "=== REMOTE URL ==="
git remote -v

echo "=== STATUS ==="
git status

echo "=== FETCH ==="
git fetch origin

echo "=== LOCAL COMMIT ==="
git rev-parse HEAD

echo "=== REMOTE COMMIT ==="
git ls-remote origin HEAD

echo "=== CODE DIFF ==="
git diff origin/main -- '*.py' '*.html' '*.json' '*.yaml' '*.md' '*.txt'

echo "=== UNTRACKED FILES ==="
git ls-files --others --exclude-standard
