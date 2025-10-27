# TradingAgents Operations Guide

This directory contains operational guides and best practices for running TradingAgents in production.

## Quick Links

- [Docker Quick Start](../../DOCKER_QUICKSTART.md) - Get started in 5 minutes
- [Deployment Guide](../../DEPLOYMENT.md) - Complete production deployment documentation
- [Environment Configuration](./environment-configuration.md) - Detailed environment variables
- [Scaling Guide](./scaling-guide.md) - How to scale TradingAgents services
- [Monitoring Guide](./monitoring-guide.md) - Observability and metrics
- [Security Guide](./security-guide.md) - Security best practices
- [Backup & Recovery](./backup-recovery.md) - Data backup and disaster recovery

## Documentation Structure

### Getting Started
- **DOCKER_QUICKSTART.md** - 5-minute setup guide for Docker
- **DEPLOYMENT.md** - Comprehensive deployment guide covering all deployment scenarios

### Operations Guides
- **environment-configuration.md** - Complete environment variable reference
- **scaling-guide.md** - Horizontal and vertical scaling strategies
- **monitoring-guide.md** - Metrics, logging, and alerting setup
- **security-guide.md** - Security hardening and best practices
- **backup-recovery.md** - Backup strategies and disaster recovery

## Common Tasks

### Initial Deployment

```bash
# 1. Setup environment
cp .env.docker .env
nano .env  # Configure API keys and passwords

# 2. Start services
./scripts/deploy.sh up

# 3. Verify health
./scripts/healthcheck.sh
```

### Scaling

```bash
# Scale backend API
docker compose up -d --scale backend=3

# Scale workers
docker compose --profile workers up -d --scale worker=5
```

### Updates and Rollbacks

```bash
# Pull latest changes
git pull

# Build new images
./scripts/deploy.sh build

# Rolling update
docker compose up -d --no-deps --build backend

# Rollback if needed
docker compose up -d --no-deps backend:previous-tag
```

### Monitoring

```bash
# View logs
./scripts/deploy.sh logs -f

# Check resource usage
docker stats

# Health check
./scripts/healthcheck.sh

# Access metrics
curl http://localhost:8000/metrics
```

### Maintenance

```bash
# Database backup
docker compose exec postgres pg_dump -U tradingagents tradingagents > backup.sql

# Database migration
./scripts/deploy.sh migrate

# Clean up unused resources
docker system prune -a
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Nginx (Optional)                     │
│                  Reverse Proxy & Load Balancer              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ├─────────────────────┐
                            │                     │
                            ▼                     ▼
                    ┌──────────────┐    ┌──────────────┐
                    │   Frontend   │    │   Backend    │
                    │   (Next.js)  │    │   (FastAPI)  │
                    └──────────────┘    └──────────────┘
                                               │
                            ┌──────────────────┼──────────────────┐
                            │                  │                  │
                            ▼                  ▼                  ▼
                    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
                    │  PostgreSQL  │  │    Redis     │  │   Workers    │
                    │   Database   │  │    Cache     │  │  (Optional)  │
                    └──────────────┘  └──────────────┘  └──────────────┘
```

## Service Responsibilities

### Backend (FastAPI)
- REST API endpoints
- WebSocket connections for real-time updates
- SSE (Server-Sent Events) streaming
- LangGraph workflow orchestration
- Database operations
- LLM API integration

### PostgreSQL
- Persistent data storage
- Session state
- Historical data
- Configuration storage

### Redis
- Session caching
- Pub/sub for worker communication
- Rate limiting
- Temporary data storage

### Workers (Optional)
- Background task processing
- Data fetching and preprocessing
- Scheduled jobs
- Heavy computation offloading

### Frontend (Optional)
- User interface
- Control Center dashboard
- Real-time session monitoring
- Configuration management

### Nginx (Optional)
- Reverse proxy
- Load balancing
- SSL/TLS termination
- Static file serving
- Rate limiting

## Environment Profiles

### Development
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```
- Hot reload enabled
- Debug logging
- Source mounting
- No resource limits

### Staging
```bash
PROFILE=frontend,workers ./scripts/deploy.sh up
```
- Production-like configuration
- All services enabled
- Moderate resource limits
- Enhanced logging

### Production
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile frontend --profile workers --profile nginx up -d
```
- Optimized for performance
- Resource limits enforced
- Auto-restart enabled
- High availability configuration

## Best Practices

### Security
1. Always use strong, unique passwords
2. Enable SSL/TLS in production
3. Use Docker secrets for sensitive data
4. Keep images updated
5. Implement network segmentation
6. Enable rate limiting

### Performance
1. Set appropriate resource limits
2. Use connection pooling
3. Enable Redis caching
4. Scale horizontally for increased load
5. Monitor and optimize database queries
6. Use CDN for static assets

### Reliability
1. Implement health checks
2. Set up automated backups
3. Configure alerting
4. Use rolling updates
5. Plan for disaster recovery
6. Document runbooks

### Monitoring
1. Collect application logs
2. Track system metrics
3. Monitor LLM API usage
4. Set up alerting thresholds
5. Regular performance reviews

## Troubleshooting Resources

### Common Issues
- Services not starting → Check logs and environment variables
- Connection errors → Verify network connectivity and service health
- Performance issues → Review resource usage and optimize configuration
- Migration failures → Check database state and Alembic history

### Diagnostic Commands
```bash
# Service status
docker compose ps

# View logs
./scripts/deploy.sh logs [service]

# Check configuration
docker compose config

# Resource usage
docker stats

# Health check
./scripts/healthcheck.sh

# Database connection
docker compose exec backend python -c "from app.db import get_db_manager; import asyncio; asyncio.run(get_db_manager().ping())"
```

## Support and Community

- **Discord**: Join our [community server](https://discord.com/invite/hk9PGKShPK)
- **GitHub Issues**: Report bugs and request features
- **Documentation**: Check our guides and API docs
- **Email**: Contact support@tauric.ai for enterprise support

## Contributing to Operations

We welcome contributions to improve our operational documentation and tooling:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

Areas we'd love help with:
- Additional deployment targets (Kubernetes, Cloud platforms)
- Monitoring and observability integrations
- Performance optimization guides
- Security hardening scripts
- Automation tools and CI/CD pipelines

## License

This documentation is part of TradingAgents and follows the same license terms.
