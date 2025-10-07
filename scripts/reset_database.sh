#!/bin/bash
# Reset codebase_mcp database - wipes all data, recreates tables

set -e  # Exit on error

PSQL="/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
DB="codebase_mcp"
SQL_FILE="/Users/cliffclarke/Claude_Code/codebase-mcp/init_tables.sql"

echo "🗑️  Resetting database: $DB"
echo ""

# Option 1: Full reset (drop all tables and recreate)
echo "Dropping all tables..."
$PSQL -d $DB -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO cliffclarke; GRANT ALL ON SCHEMA public TO public;" > /dev/null 2>&1

echo "Recreating tables..."
$PSQL -d $DB -f $SQL_FILE > /dev/null 2>&1

echo ""
echo "✅ Database reset complete!"
echo ""
echo "Tables created:"
$PSQL -d $DB -c "\dt" | grep public

echo ""
echo "Ready to use. Restart Claude Desktop to reconnect."
