#!/bin/bash
# ShaktiDB UTF-8 Verification & Diagnostic Script
# Run this after docker-compose up to verify UTF-8 initialization

set -e

CONTAINER_NAME="shakti-db"
DB_USER="postgres"

echo "═══════════════════════════════════════════════════════════════"
echo "ShaktiDB UTF-8 Verification Script"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check if container is running
if ! docker ps --filter "name=$CONTAINER_NAME" --format "{{.Names}}" | grep -q "$CONTAINER_NAME"; then
  echo "❌ Container '$CONTAINER_NAME' is not running"
  echo "   Run: docker-compose up -d"
  exit 1
fi
echo "✓ Container is running: $CONTAINER_NAME"
echo ""

# Check 1: Locale availability
echo "─── Check 1: Locale Availability ───"
if docker exec "$CONTAINER_NAME" locale -a 2>/dev/null | grep -q "en_US.utf8"; then
  echo "✓ en_US.UTF-8 locale is available"
else
  echo "❌ en_US.UTF-8 locale NOT found"
  echo "   This will cause SQL_ASCII encoding"
  exit 1
fi
echo ""

# Check 2: Database readiness
echo "─── Check 2: Database Readiness ───"
if docker exec "$CONTAINER_NAME" pg_isready -U "$DB_USER" -h localhost -p 15234 >/dev/null 2>&1; then
  echo "✓ Database is accepting connections"
else
  echo "❌ Database is not ready yet"
  echo "   This may be normal if the container just started"
  echo "   Wait a few seconds and try again: docker exec $CONTAINER_NAME pg_isready -U $DB_USER"
  exit 1
fi
echo ""

# Check 3: Server encoding
echo "─── Check 3: Server Encoding (CRITICAL) ───"
server_encoding=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -t -c "SHOW server_encoding;" 2>/dev/null | xargs)
if [ "$server_encoding" = "UTF8" ]; then
  echo "✓ server_encoding = $server_encoding (CORRECT)"
else
  echo "❌ server_encoding = $server_encoding (WRONG - should be UTF8)"
  echo ""
  echo "   This indicates the cluster was initialized with the wrong encoding."
  echo "   RECOVERY STEPS:"
  echo "   1. Stop containers: docker-compose down"
  echo "   2. Remove volume: docker volume rm rag-system_shakti-db-data"
  echo "   3. Rebuild image: docker build -t shaktidb:17.4 infra/shaktidb/"
  echo "   4. Restart: docker-compose up -d"
  exit 1
fi
echo ""

# Check 4: Locale categories
echo "─── Check 4: Locale Categories ───"
lc_collate=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -t -c "SHOW lc_collate;" 2>/dev/null | xargs)
lc_ctype=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -t -c "SHOW lc_ctype;" 2>/dev/null | xargs)
lc_messages=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -t -c "SHOW lc_messages;" 2>/dev/null | xargs)

echo "  lc_collate  = $lc_collate"
echo "  lc_ctype    = $lc_ctype"
echo "  lc_messages = $lc_messages"

if [[ "$lc_collate" == "en_US.UTF-8" ]] || [[ "$lc_collate" == "C" ]]; then
  echo "✓ Locale categories are properly configured"
else
  echo "⚠ Unexpected locale setting; verify it's UTF-8 compatible"
fi
echo ""

# Check 5: Client encoding
echo "─── Check 5: Client Encoding ───"
client_encoding=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -t -c "SHOW client_encoding;" 2>/dev/null | xargs)
echo "  client_encoding = $client_encoding"
if [ "$client_encoding" = "UTF8" ]; then
  echo "✓ Client encoding is UTF8"
else
  echo "⚠ Client encoding is not UTF8; connections may need SET client_encoding='UTF8'"
fi
echo ""

# Check 6: Unicode data insertion test
echo "─── Check 6: Unicode Data Test ───"
if docker exec "$CONTAINER_NAME" psql -U "$DB_USER" <<'EOF' >/dev/null 2>&1
CREATE TABLE IF NOT EXISTS unicode_test (id SERIAL PRIMARY KEY, text TEXT);
INSERT INTO unicode_test (text) VALUES ('en dash: –');
INSERT INTO unicode_test (text) VALUES ('emoji: 🚀');
INSERT INTO unicode_test (text) VALUES ('Chinese: 你好');
INSERT INTO unicode_test (text) VALUES ('Arabic: مرحبا');
SELECT COUNT(*) FROM unicode_test;
DROP TABLE unicode_test;
EOF
then
  echo "✓ Unicode insertion test passed (multi-language support working)"
else
  echo "❌ Unicode insertion test FAILED"
  echo "   This indicates encoding issues in the database"
  exit 1
fi
echo ""

# Check 7: PDF-relevant Unicode test
echo "─── Check 7: PDF Special Character Test ───"
if docker exec "$CONTAINER_NAME" psql -U "$DB_USER" <<'EOF' >/dev/null 2>&1
CREATE TABLE IF NOT EXISTS pdf_chars (id SERIAL PRIMARY KEY, text TEXT);
-- Common PDF extract characters
INSERT INTO pdf_chars (text) VALUES ('En dash (PDF): – – –');
INSERT INTO pdf_chars (text) VALUES ('Em dash (PDF): — — —');
INSERT INTO pdf_chars (text) VALUES ('Smart quotes: " " ' '');
INSERT INTO pdf_chars (text) VALUES ('Bullet: • ◦ ◆');
INSERT INTO pdf_chars (text) VALUES ('Math: ± × ÷ √ ∞');
SELECT COUNT(*) FROM pdf_chars;
DROP TABLE pdf_chars;
EOF
then
  echo "✓ PDF character test passed (safe for PDF ingestion)"
else
  echo "❌ PDF character test FAILED"
  echo "   PDF text extraction may fail with encoding errors"
  exit 1
fi
echo ""

# Final summary
echo "═══════════════════════════════════════════════════════════════"
echo "✓ All checks passed! Database is UTF-8 ready."
echo ""
echo "You can now:"
echo "  • Start the RAG pipeline"
echo "  • Ingest PDF documents (Unicode text will be preserved)"
echo "  • Query with multi-language text"
echo ""
echo "To see detailed logs:"
echo "  docker logs $CONTAINER_NAME | grep -E '\\[OK\\]|\\[ERROR\\]|\\[STEP\\]'"
echo ""
echo "To inspect PostgreSQL configuration:"
echo "  docker exec -it $CONTAINER_NAME psql -U postgres"
echo "  postgres=# \\l"
echo "═══════════════════════════════════════════════════════════════"
