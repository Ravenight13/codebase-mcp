#!/bin/bash
# Entrypoint script for Codebase MCP Server Docker container
# Responsibilities:
# 1. Wait for PostgreSQL to be available
# 2. Run database migrations (alembic upgrade head)
# 3. Start the MCP server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ============================================================================
# Wait for PostgreSQL to be ready
# ============================================================================
log_info "Waiting for PostgreSQL to be available..."

DB_HOST="${DB_HOST:-postgresql}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${POSTGRES_USER:-postgres}"
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" > /dev/null 2>&1; then
        log_info "PostgreSQL is ready!"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    WAIT_TIME=$((RETRY_COUNT * 2))
    echo "Attempt $RETRY_COUNT/$MAX_RETRIES: PostgreSQL not ready, waiting ${WAIT_TIME}s..."
    sleep "$WAIT_TIME"
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    log_error "PostgreSQL did not become available after ${MAX_RETRIES} attempts"
    exit 1
fi

# ============================================================================
# Run database migrations
# ============================================================================
log_info "Running database migrations..."

cd /app

# Use DATABASE_URL if set, otherwise use REGISTRY_DATABASE_URL (modern naming)
if [ -z "$DATABASE_URL" ] && [ -n "$REGISTRY_DATABASE_URL" ]; then
    export DATABASE_URL="$REGISTRY_DATABASE_URL"
fi

if [ -z "$DATABASE_URL" ]; then
    log_error "DATABASE_URL or REGISTRY_DATABASE_URL environment variable not set"
    exit 1
fi

if ! alembic upgrade head; then
    log_error "Database migrations failed"
    log_warn "Container will still start, but may have schema issues"
    log_warn "Check database logs and re-run migrations manually if needed"
fi

log_info "Migrations completed (or already up to date)"

# ============================================================================
# Start the MCP server
# ============================================================================
log_info "Starting Codebase MCP Server..."

# Execute the server process (replacing the shell with the Python process)
# This is important for proper signal handling (SIGTERM for graceful shutdown)
exec python src/mcp/server_fastmcp.py

