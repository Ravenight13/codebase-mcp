# Deployment Documentation

This directory contains comprehensive guides for deploying Codebase MCP Server in different environments and scenarios.

## Quick Navigation

### For First-Time Users
Start here if you're new to Docker and containerization:
- **[DOCKER_SETUP.md](DOCKER_SETUP.md)** - Get started with Docker Compose locally in 5 minutes

### For Local Development
- **[DOCKER_SETUP.md](DOCKER_SETUP.md)** - Set up a complete development environment with Docker Compose
  - Hot reload for code changes
  - Local PostgreSQL and Ollama services
  - Integrated database for testing
  - Verified working end-to-end scenarios

### For Production Deployment
- **[PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)** - Deploy to production with external services
  - Single Docker image, multiple instances for scaling
  - External PostgreSQL and Ollama configuration
  - Health check verification
  - Multi-instance load balancing
  - Graceful upgrades and rolling deployments

### For CI/CD Integration
- **[CI_CD_INTEGRATION.md](CI_CD_INTEGRATION.md)** - Automate builds and testing
  - GitHub Actions example workflow
  - Docker layer caching optimization
  - Fast builds (2-3min full, <30s code changes)
  - Test artifact collection (coverage reports)
  - Expected performance targets

### For Health & Monitoring
- **[HEALTH_CHECKS.md](HEALTH_CHECKS.md)** - Monitor service health
  - Health check configuration for each service
  - Manual health verification commands
  - Failure troubleshooting and recovery
  - Monitoring best practices

### For Troubleshooting
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Debug and fix common issues
  - Port conflicts and networking
  - Service startup problems
  - Database migration failures
  - Connection refused errors
  - Memory and resource issues
  - Debug procedures and shell access

## Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│                    Docker Network                    │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────────┐    ┌──────────────────┐      │
│  │   PostgreSQL     │    │      Ollama      │      │
│  │   Port: 5432     │    │   Port: 11434    │      │
│  │  pgvector ready  │    │ Embeddings API   │      │
│  └────────┬─────────┘    └────────┬─────────┘      │
│           │                       │                 │
│           └───────────┬───────────┘                 │
│                       │                             │
│            ┌──────────▼──────────┐                 │
│            │  Codebase MCP       │                 │
│            │  Server (FastMCP)   │                 │
│            │  - Indexing         │                 │
│            │  - Searching        │                 │
│            │  - Task Management  │                 │
│            └─────────────────────┘                 │
│                                                      │
└──────────────────────────────────────────────────────┘
```

**Key Components:**
- **PostgreSQL**: Data storage with pgvector for semantic search
- **Ollama**: Embedding generation service (nomic-embed-text model)
- **Codebase MCP**: Main server handling indexing, search, and task management

## Service Specifications

| Service | Port | Health Check | Startup Time | Purpose |
|---------|------|--------------|--------------|---------|
| PostgreSQL | 5432 | `pg_isready` | ~2-5 seconds | Code storage, embeddings, metadata |
| Ollama | 11434 | HTTP `/api/tags` | ~5-20 seconds | Embedding generation |
| Codebase MCP | stdio | `pgrep` process check | ~10-20 seconds | MCP server, indexing, search |

## Deployment Scenarios

### Scenario 1: Local Development
**Use Case**: Developing features, testing changes locally

**Setup**: `docker-compose up`
**Time to Ready**: <2 minutes
**Features**: Hot reload, full services, testing ready
**Guide**: [DOCKER_SETUP.md](DOCKER_SETUP.md)

### Scenario 2: Production Single Instance
**Use Case**: Small teams, single deployment, managed databases

**Setup**: Docker run with environment variables
**Time to Deploy**: <1 minute after building image
**Features**: Health checks, auto-restart, rolling updates
**Guide**: [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)

### Scenario 3: Production Scaled (Load Balanced)
**Use Case**: High-traffic deployments, multiple teams, load distribution

**Setup**: Multiple Docker containers + load balancer (nginx, HAProxy)
**Time to Deploy**: <5 minutes for N instances
**Features**: Horizontal scaling, shared databases, distributed search
**Guide**: [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) - Scaling section

### Scenario 4: CI/CD Integration
**Use Case**: Automated testing, build validation, artifact collection

**Setup**: Docker-compose in CI pipeline
**Build Time**: <30 seconds (code change), 2-3 minutes (full build)
**Guide**: [CI_CD_INTEGRATION.md](CI_CD_INTEGRATION.md)

## Performance Targets

All deployments aim to meet these constitutional performance targets:

| Metric | Target | Verification |
|--------|--------|--------------|
| Stack Startup | <120 seconds | `docker-compose ps` - all healthy |
| Image Size | <500 MB | `docker images` - confirmed <500MB |
| Server Readiness | <30 seconds | Health check status in logs |
| Database Migrations | Auto on startup | Check logs for "migrations complete" |
| Search Latency | <500ms p95 | Search performance tests |
| Indexing Rate | <60s for 10K files | Indexing job completion status |

## Environment Variables

**Required for all deployments:**
```bash
REGISTRY_DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database
OLLAMA_BASE_URL=http://ollama:11434
```

**Optional (sensible defaults provided):**
```bash
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_BATCH_SIZE=32
LOG_LEVEL=INFO
DATABASE_POOL_MAX_SIZE=20
```

See individual guides for environment variable documentation.

## File Structure

```
docs/deployment/
├── README.md                    # This file - navigation and overview
├── DOCKER_SETUP.md             # Local development with Docker Compose
├── PRODUCTION_DEPLOYMENT.md    # Production deployment guide
├── TROUBLESHOOTING.md          # Common issues and solutions
├── HEALTH_CHECKS.md            # Monitoring and health configuration
└── CI_CD_INTEGRATION.md        # CI/CD pipeline integration
```

## Getting Help

### Common Questions

**Q: Should I use Docker?**
A: Yes. Docker eliminates "works on my machine" issues and makes deployment consistent across dev, test, and prod.

**Q: Can I run without Docker?**
A: Yes. See the manual setup section in the main README, but you'll need to manage PostgreSQL, Ollama, and dependencies yourself.

**Q: What's the performance impact of Docker?**
A: Minimal. Docker adds <50ms latency. Performance targets are met with comfortable margins.

**Q: How do I scale to multiple servers?**
A: Run multiple MCP containers pointing to the same PostgreSQL and Ollama services. Use a load balancer (nginx, HAProxy) to distribute traffic.

**Q: Can I use managed databases (AWS RDS, etc)?**
A: Yes. Set `REGISTRY_DATABASE_URL` to your managed database connection string in PRODUCTION_DEPLOYMENT.md.

### Troubleshooting Quick Links

- Services won't start → [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Health check failing → [HEALTH_CHECKS.md](HEALTH_CHECKS.md)
- Build slow → [CI_CD_INTEGRATION.md](CI_CD_INTEGRATION.md#Layer-Caching)
- Connection errors → [TROUBLESHOOTING.md](TROUBLESHOOTING.md#Connection-Refused-Errors)

### Getting More Help

1. **Check the relevant guide** based on your scenario above
2. **Review [TROUBLESHOOTING.md](TROUBLESHOOTING.md)** for your specific error
3. **Check logs**: `docker-compose logs <service>`
4. **File an issue** on GitHub with logs and reproduction steps

## Best Practices

### Security
- ✅ Use environment variables for secrets (PostgreSQL passwords)
- ✅ Don't commit `.env` files to git (use `.env.example`)
- ✅ Use `secrets management` tools in production (AWS Secrets Manager, HashiCorp Vault)
- ✅ Run containers as non-root user (already configured)

### Performance
- ✅ Use named volumes for database persistence (faster than bind mounts)
- ✅ Enable Docker layer caching for faster builds (configured in Dockerfile)
- ✅ Monitor resource usage: `docker stats`
- ✅ Tune database pool size based on workload

### Reliability
- ✅ Use health checks (enabled by default)
- ✅ Configure restart policies (`unless-stopped` for production)
- ✅ Monitor logs regularly (`docker logs -f`)
- ✅ Set up alerting on health check failures

### Maintenance
- ✅ Regular database backups
- ✅ Plan migrations during low-traffic periods
- ✅ Keep Docker images up to date
- ✅ Test upgrades in staging environment first

## Migration Path

**From Manual Setup to Docker**:
1. Keep existing PostgreSQL and Ollama running
2. Set environment variables pointing to them
3. Build and run Docker image
4. Verify search and indexing work
5. Gradually migrate data if needed
6. Decommission manual setup

**From Development to Production**:
1. Test locally with `docker-compose up`
2. Build production image: `docker build -t codebase-mcp:vX.Y.Z .`
3. Deploy to production using PRODUCTION_DEPLOYMENT.md guide
4. Run smoke tests
5. Monitor logs for 24 hours
6. Set up alerting

## Related Documentation

- **[Project README](../../README.md)** - Feature overview and quick start
- **[API Reference](../api/tool-reference.md)** - MCP tool documentation
- **[Architecture](../architecture/multi-project-design.md)** - System design details
- **[Configuration](../configuration/production-config.md)** - Tuning and optimization

---

**Last Updated**: November 2025
**Status**: Production Ready ✅
**Docker Support**: Version 0.15.0+
