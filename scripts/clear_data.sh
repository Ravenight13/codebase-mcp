#!/bin/bash
# Clear all data from codebase_mcp database (keeps schema intact)

set -e

PSQL="/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
DB="codebase_mcp"

echo "🗑️  Clearing all data from: $DB"
echo ""

$PSQL -d $DB << 'EOF'
TRUNCATE TABLE 
  search_queries,
  embedding_metadata,
  change_events,
  task_status_history,
  task_commit_links,
  task_branch_links,
  task_planning_references,
  tasks,
  code_chunks,
  code_files,
  repositories
CASCADE;
EOF

echo ""
echo "✅ All data cleared! Tables still exist but are empty."
echo ""
echo "Row counts:"
$PSQL -d $DB -c "SELECT 'repositories' as table, COUNT(*) FROM repositories UNION ALL SELECT 'code_files', COUNT(*) FROM code_files UNION ALL SELECT 'code_chunks', COUNT(*) FROM code_chunks UNION ALL SELECT 'tasks', COUNT(*) FROM tasks;"

echo ""
echo "Ready to use. No restart needed."
