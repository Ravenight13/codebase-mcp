# Database Reset Scripts

Three options for resetting your `codebase_mcp` database during development.

## Quick Reference

| Script | What It Does | Speed | Restart Required? |
|--------|--------------|-------|-------------------|
| `./scripts/clear_data.sh` | Delete all data, keep schema | Fast (1s) | ❌ No |
| `./scripts/reset_database.sh` | Drop & recreate all tables | Medium (2s) | ⚠️ Recommended |
| `./scripts/nuclear_reset.sh` | Drop entire database | Slow (3s) | ✅ Yes |

---

## Option 1: Clear Data Only (Fastest)

**Use when:** You want to wipe data but keep the schema intact.

```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp
./scripts/clear_data.sh
```

**What it does:**
- `TRUNCATE` all 11 tables (preserves structure)
- Clears all tasks, repositories, code chunks, etc.
- Keeps indexes, constraints, and table definitions
- No restart needed

**Time:** ~1 second

---

## Option 2: Reset Database (Recommended)

**Use when:** You want a completely clean slate with fresh schema.

```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp
./scripts/reset_database.sh
```

**What it does:**
- `DROP SCHEMA public CASCADE` (removes all tables)
- `CREATE SCHEMA public` (fresh schema)
- Recreates all 11 tables from `init_tables.sql`
- Rebuilds all indexes and constraints

**Time:** ~2 seconds  
**Restart:** Recommended (but usually works without)

---

## Option 3: Nuclear Reset (Slowest)

**Use when:** You want to drop the entire database and start from absolute zero.

```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp
./scripts/nuclear_reset.sh
```

**What it does:**
- Asks for confirmation (safety check)
- `DROP DATABASE codebase_mcp`
- `CREATE DATABASE codebase_mcp`
- Recreates all tables from `init_tables.sql`

**Time:** ~3 seconds  
**Restart:** **REQUIRED** - Claude Desktop loses connection

---

## After Reset

### Verify Reset Worked

```bash
psql -d codebase_mcp -c "SELECT 'tasks' as table, COUNT(*) as rows FROM tasks;"
```

Should show 0 rows.

### Restart Claude Desktop (if needed)

1. **Quit:** Cmd+Q (don't just close window)
2. **Reopen:** Launch Claude Desktop from Applications
3. **Verify:** Check 🔨 Tools menu shows 6 tools

### Test Your Tools

```
Create a test task to verify everything works:
"Create a task called 'Database Reset Test' with description 'Verifying clean database'"
```

---

## Manual Alternatives

If you prefer manual control:

### Just Drop All Tables
```bash
psql -d codebase_mcp -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
psql -d codebase_mcp -f init_tables.sql
```

### Just Clear Data
```bash
psql -d codebase_mcp << 'EOF'
TRUNCATE TABLE 
  search_queries, embedding_metadata, change_events,
  task_status_history, task_commit_links, task_branch_links,
  task_planning_references, tasks, code_chunks, code_files, repositories
CASCADE;
EOF
```

---

## Troubleshooting

### "Database does not exist"
Run `nuclear_reset.sh` to recreate from scratch.

### "Permission denied"
Scripts need execute permissions:
```bash
chmod +x *.sh
```

### "Server disconnected" after reset
Restart Claude Desktop (Cmd+Q, then reopen).

### Want to keep some data?
Manually delete from specific tables:
```bash
psql -d codebase_mcp -c "DELETE FROM tasks WHERE created_at < NOW() - INTERVAL '7 days';"
```

---

## Best Practices

**During Development:**
- Use `./scripts/clear_data.sh` for quick resets between tests
- No need to restart Claude Desktop

**After Schema Changes:**
- Use `./scripts/reset_database.sh` to rebuild tables
- Restart recommended but not always required

**When Things Are Broken:**
- Use `./scripts/nuclear_reset.sh` for complete clean slate
- Always restart Claude Desktop after this

**Before Production:**
- Never use these scripts on production databases
- Use proper migration tools (Alembic) instead
