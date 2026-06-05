#!/bin/bash

BASE="https://eu-funds-and-grants-ai.onrender.com"

echo "=== HEALTH ==="
curl -s $BASE/health | jq .

echo "=== GRANTS ==="
curl -s $BASE/grants | jq .

echo "=== LOCAL GRANTS ==="
curl -s $BASE/grants/local | jq .

echo "=== URGENT GRANTS ==="
curl -s "$BASE/grants/urgent?days=30" | jq .

echo "=== SEARCH ==="
curl -s -X POST $BASE/search \
  -H "Content-Type: application/json" \
  -d '{"query":"EU fondovi"}' | jq .

echo "=== AI ANSWER ==="
curl -s -X POST $BASE/ai-answer \
  -H "Content-Type: application/json" \
  -d '{"query":"Kako aplicirati za EU grant?"}' | jq .

echo "=== EMBED ==="
curl -s -X POST $BASE/api/embed \
  -H "Content-Type: application/json" \
  -d '{"text":"EU grantovi"}' | jq .

echo "=== AUTH REGISTER ==="
curl -s -X POST $BASE/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test","password":"test"}' | jq .

echo "=== AUTH LOGIN ==="
curl -s -X POST $BASE/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test","password":"test"}' | jq .

