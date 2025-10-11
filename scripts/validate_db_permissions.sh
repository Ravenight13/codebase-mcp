#!/bin/bash
set -e

echo "🔍 Validating PostgreSQL setup and permissions..."
echo ""

# Check PostgreSQL version
echo "1️⃣ Checking PostgreSQL version..."
PG_VERSION=$(psql --version | grep -oE '[0-9]+\.[0-9]+' | head -1)
PG_MAJOR=$(echo "$PG_VERSION" | cut -d'.' -f1)

if [ "$PG_MAJOR" -lt 14 ]; then
    echo "❌ PostgreSQL version $PG_VERSION is too old. Version 14 or higher required."
    echo "   Install with: brew install postgresql@14"
    exit 1
fi
echo "✅ PostgreSQL version $PG_VERSION is supported"
echo ""

# Detect current user
DB_USER=$(whoami)

# Verify pgvector extension
echo "2️⃣ Checking pgvector extension..."
if psql -U "$DB_USER" -d postgres -c "CREATE EXTENSION IF NOT EXISTS vector;" &>/dev/null; then
    echo "✅ pgvector extension is available"
else
    echo "❌ pgvector extension is not available"
    echo "   Install with: brew install pgvector"
    exit 1
fi
echo ""

# Test CREATEDB permission
echo "3️⃣ Testing CREATEDB permission..."
TEMP_DB="temp_test_db_$$"
if psql -U "$DB_USER" -d postgres <<EOF 2>/dev/null
CREATE DATABASE $TEMP_DB;
DROP DATABASE $TEMP_DB;
EOF
then
    echo "✅ User $DB_USER has CREATEDB permission"
else
    echo "❌ User $DB_USER lacks CREATEDB permission"
    echo "   Fix with: psql -U postgres -c \"ALTER ROLE $DB_USER CREATEDB;\""
    exit 1
fi
echo ""

# Test dynamic database creation
echo "4️⃣ Testing dynamic database creation..."
TEST_DB="test_multiproject_$(date +%s)"
psql -U "$DB_USER" -d postgres <<EOF
CREATE DATABASE $TEST_DB;
EOF

echo "   ✅ Created database $TEST_DB"

psql -U "$DB_USER" -d "$TEST_DB" <<EOF
CREATE SCHEMA codebase;
CREATE TABLE codebase.test (id SERIAL);
EOF

echo "   ✅ Created schema and table"

psql -U "$DB_USER" -d postgres <<EOF
DROP DATABASE $TEST_DB;
EOF

echo "   ✅ Dropped test database"
echo ""

echo "🎉 All database permission checks passed!"
echo ""
echo "Summary:"
echo "  ✓ PostgreSQL $PG_VERSION installed"
echo "  ✓ pgvector extension available"
echo "  ✓ CREATEDB permission granted"
echo "  ✓ Dynamic database creation works"
