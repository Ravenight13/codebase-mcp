#!/bin/bash
# NUCLEAR OPTION: Drop entire database and recreate from scratch

set -e

PSQL="/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
DB="codebase_mcp"
SQL_FILE="/Users/cliffclarke/Claude_Code/codebase-mcp/init_tables.sql"

echo "☢️  NUCLEAR RESET: Dropping entire database: $DB"
echo ""
read -p "Are you sure? This will delete EVERYTHING. (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "Dropping database..."
$PSQL -d postgres -c "DROP DATABASE IF EXISTS $DB;" 2>/dev/null || true

echo "Creating database..."
$PSQL -d postgres -c "CREATE DATABASE $DB OWNER cliffclarke;"

echo "Recreating tables..."
$PSQL -d $DB -f $SQL_FILE > /dev/null 2>&1

echo ""
echo "✅ Nuclear reset complete!"
echo ""
echo "Tables created:"
$PSQL -d $DB -c "\dt" | grep public

echo ""
echo "⚠️  IMPORTANT: Restart Claude Desktop to reconnect!"
