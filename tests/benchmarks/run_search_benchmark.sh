#!/usr/bin/env bash
set -euo pipefail

API="${API:-https://eu-funds-and-grants-ai.onrender.com}"
TOKEN="${TOKEN:-}"
trap 'unset TOKEN AUTH_RESPONSE EMAIL response' EXIT
RUN_ID="$(date +%Y_%m_%d_%H%M%S)"
RESULT_DIR="tests/benchmarks/results/${RUN_ID}"
SUMMARY="${RESULT_DIR}/SUMMARY.md"

if [ -z "$TOKEN" ]; then
    read -r -s -p "Paste application JWT token: " TOKEN
    echo
fi

for command in curl jq; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "[ERROR] Nedostaje naredba: $command"
        exit 1
    fi
done

mkdir -p "$RESULT_DIR"
chmod 700 "$RESULT_DIR"

echo "[INFO] Provjera JWT tokena..."

AUTH_RESPONSE="$(
    curl --fail-with-body -sS "$API/auth/me" \
        -H "Authorization: Bearer $TOKEN"
)"

if ! printf '%s' "$AUTH_RESPONSE" | jq -e '.email' >/dev/null 2>&1; then
    echo "[ERROR] JWT token nije valjan:"
    printf '%s\n' "$AUTH_RESPONSE" | jq .
    exit 1
fi

EMAIL="$(printf '%s' "$AUTH_RESPONSE" | jq -r '.email')"

cat > "$SUMMARY" <<EOF_SUMMARY
# FinAssistBH Search Benchmark

- Run ID: $RUN_ID
- API: $API
- Authentication: PASS
- Authentication account: validated, not written to benchmark artifacts
- Requested results per query: 10

EOF_SUMMARY

queries=(
    "grant za digitalizaciju firme u ZDK"
    "digitalizacija proizvodne firme Tešanj"
    "ERP sistem za MSP"
    "CNC proizvodnja Tešanj"
    "AI startup BiH"
    "tehnološki startup ZDK"
    "Poticaji za poljoprivredu u BiH"
    "farma mlijeka ZDK"
    "poticaji za pčelarstvo"
    "voćnjak poticaji FBiH"
    "ruralni razvoj BiH"
    "grantovi za obrt u Tešnju"
    "zapošljavanje mladih u FBiH"
    "energetska efikasnost MSP"
    "izvoz i konkurentnost firme"
)

index=0

for query in "${queries[@]}"; do
    index=$((index + 1))
    number="$(printf '%02d' "$index")"
    output="${RESULT_DIR}/${number}.json"

    echo "[TEST $number/${#queries[@]}] $query"

    response="$(
        curl --fail-with-body -sS \
            -X POST "$API/search" \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            -d "$(jq -n --arg query "$query" \
                '{query: $query, n_results: 10}')"
    )"

    printf '%s\n' "$response" | jq . > "$output"

    {
        echo "## $number. $query"
        echo

        if printf '%s' "$response" |
            jq -e '.metadatas[0] | type == "array"' >/dev/null 2>&1; then

            printf '%s' "$response" |
                jq -r '.metadatas[0][] |
                "- " + (.title // "Bez naslova")'

            processing_time="$(
                printf '%s' "$response" |
                    jq -r '.processing_time // "N/A"'
            )"

            echo
            echo "Processing time: ${processing_time}s"
        else
            echo "- ERROR: Neočekivani API odgovor"
            echo
            echo '```json'
            printf '%s\n' "$response" | jq .
            echo '```'
        fi

        echo
    } >> "$SUMMARY"

    sleep 1
done

unset TOKEN AUTH_RESPONSE EMAIL

echo "[OK] Benchmark završen."
echo "[OK] Rezultati: $RESULT_DIR"
echo "[OK] Sažetak: $SUMMARY"
