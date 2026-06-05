#!/bin/bash
set -e
# compare_code.sh - uporedi samo kod (py, html, yaml, json, md, txt) lokalno vs origin/main

TMP_LOCAL=/tmp/local_code_$$
TMP_REMOTE=/tmp/remote_code_$$
mkdir -p "$TMP_LOCAL" "$TMP_REMOTE"

# lokalna kombinovana hash
git ls-files '*.py' '*.html' '*.yaml' '*.yml' '*.json' '*.md' '*.txt' | sort > "$TMP_LOCAL/files.txt"
( while IFS= read -r f; do
    echo "===FILE:$f==="
    cat "$f"
  done < "$TMP_LOCAL/files.txt" ) | sha256sum > "$TMP_LOCAL/combined.sha"

# remote snapshot
git archive origin/main | tar -x -C "$TMP_REMOTE"
( cd "$TMP_REMOTE"
  find . -type f \( -name '*.py' -o -name '*.html' -o -name '*.yaml' -o -name '*.yml' -o -name '*.json' -o -name '*.md' -o -name '*.txt' \) \
    | sed 's|^\./||' | sort > /tmp/remote_files.txt
  while IFS= read -r f; do
    echo "===FILE:$f==="
    cat "$f"
  done < /tmp/remote_files.txt ) | sha256sum > "$TMP_REMOTE/combined.sha"

echo "LOCAL HASH:  $(cat $TMP_LOCAL/combined.sha)"
echo "REMOTE HASH: $(cat $TMP_REMOTE/combined.sha)"

if cmp -s "$TMP_LOCAL/combined.sha" "$TMP_REMOTE/combined.sha"; then
  echo "RESULT: Code identical (for selected file types)."
else
  echo "RESULT: Code differs. Run 'git diff origin/main -- <path>' for details."
fi
