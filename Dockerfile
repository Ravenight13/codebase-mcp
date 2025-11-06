# Multi-stage Dockerfile for Codebase MCP Server
# Stage 1 (builder): Compile dependencies
# Stage 2 (runtime): Minimal production image

# ============================================================================
# Stage 1: Builder
# ============================================================================
FROM python:3.12-slim as builder

WORKDIR /build

# Install build dependencies for compiling Python packages (gcc, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies to /build/.local
# This keeps them separate from system Python packages
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ============================================================================
# Stage 2: Runtime (final image)
# ============================================================================
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies (no build tools needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 mcp && chown -R mcp:mcp /app

# Copy installed packages from builder stage
COPY --from=builder --chown=mcp:mcp /root/.local /home/mcp/.local

# Copy application source code
COPY --chown=mcp:mcp src/ /app/src/
COPY --chown=mcp:mcp alembic/ /app/alembic/
COPY --chown=mcp:mcp alembic.ini /app/

# Copy entrypoint script
COPY --chown=mcp:mcp scripts/docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set Python path to include installed packages
ENV PATH=/home/mcp/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER mcp

# Health check: Verify MCP server process is running
HEALTHCHECK --start-period=20s --interval=30s --timeout=5s --retries=3 \
    CMD pgrep -f "python.*server_fastmcp" || exit 1

# Entrypoint script handles database migrations and server startup
ENTRYPOINT ["/app/entrypoint.sh"]

# Expose as stdio server (no ports, but documented for clarity)
# The MCP server communicates via stdio/SSE to its parent process
EXPOSE 0

