#!/bin/bash
# Test the Per-ETF API functionality

echo "=========================================="
echo "🧪 Testing Per-ETF Architecture"
echo "=========================================="
echo ""

# Test 1: Check TEQ only
echo "📊 Test 1: Check TEQ only (ISIN: LU3098954871)"
echo "Expected: 8 URLs checked"
echo "Making request..."
RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
     -d '{"isin":"LU3098954871"}' \
     http://localhost:3000/api/monitor)

URL_COUNT=$(echo "$RESPONSE" | jq -r '.url_count // "error"')
CHECKED_ISIN=$(echo "$RESPONSE" | jq -r '.checked_isin // "null"')
RESULT_COUNT=$(echo "$RESPONSE" | jq -r '.results | length')

echo "✓ URL Count: $URL_COUNT"
echo "✓ Checked ISIN: $CHECKED_ISIN"
echo "✓ Result Count: $RESULT_COUNT"
echo ""

# Test 2: Check Inyova only
echo "📊 Test 2: Check Inyova only (ISIN: LU3075459852)"
echo "Expected: 8 URLs checked"
echo "Making request..."
RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
     -d '{"isin":"LU3075459852"}' \
     http://localhost:3000/api/monitor)

URL_COUNT=$(echo "$RESPONSE" | jq -r '.url_count // "error"')
CHECKED_ISIN=$(echo "$RESPONSE" | jq -r '.checked_isin // "null"')
RESULT_COUNT=$(echo "$RESPONSE" | jq -r '.results | length')

echo "✓ URL Count: $URL_COUNT"
echo "✓ Checked ISIN: $CHECKED_ISIN"
echo "✓ Result Count: $RESULT_COUNT"
echo ""

# Test 3: Check all
echo "📊 Test 3: Check ALL (no ISIN parameter)"
echo "Expected: 16 URLs checked"
echo "Making request..."
RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
     -d '{}' \
     http://localhost:3000/api/monitor)

URL_COUNT=$(echo "$RESPONSE" | jq -r '.url_count // "error"')
CHECKED_ISIN=$(echo "$RESPONSE" | jq -r '.checked_isin // "null"')
RESULT_COUNT=$(echo "$RESPONSE" | jq -r '.results | length')

echo "✓ URL Count: $URL_COUNT"
echo "✓ Checked ISIN: $CHECKED_ISIN"
echo "✓ Result Count: $RESULT_COUNT"
echo ""

echo "=========================================="
echo "✅ All tests completed!"
echo "=========================================="
