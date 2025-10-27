# Docker Quick Reference Card

Quick reference for common Docker deployment tasks.

## Initial Setup

```bash
# Clone and configure
git clone https://github.com/TauricResearch/TradingAgents.git
cd TradingAgents
cp .env.docker .env
nano .env  # Edit with your API keys

# Start services
./scripts/deploy.sh up
```

## Service Management

```bash
# Start all services
./scripts/deploy.sh up

# Start with specific profiles
PROFILE=frontend ./scripts/deploy.sh up
PROFILE=workers ./scripts/deploy.sh up
PROFILE=frontend,workers,nginx ./scripts/deploy.sh up

# Stop services
./scripts/deploy.sh down

# Restart services
./scripts/deploy.sh restart

# View status
./scripts/deploy.sh ps
```

## Logs and Monitoring

```bash
# View all logs
./scripts/deploy.sh logs

# Follow logs in real-time
./scripts/deploy.sh logs -f

# View specific service logs
./scripts/deploy.sh logs backend
./scripts/deploy.sh logs postgres

# Run health checks
./scripts/healthcheck.sh

# Monitor resources
docker stats
```

## Database Operations

```bash
# Run migrations
./scripts/deploy.sh migrate

# Backup database
docker compose exec postgres pg_dump -U tradingagents tradingagents > backup.sql

# Restore database
docker compose exec -T postgres psql -U tradingagents tradingagents < backup.sql

# Access PostgreSQL shell
docker compose exec postgres psql -U tradingagents

# Check migration status
docker compose exec backend alembic current
```

## Container Access

```bash
# Shell access to backend
./scripts/deploy.sh shell backend

# Shell access to other services
docker compose exec postgres /bin/sh
docker compose exec redis /bin/sh

# Run Python commands
docker compose exec backend python -c "print('Hello')"

# Execute backend CLI
docker compose exec backend python -m cli.main
```

## Scaling

```bash
# Scale backend horizontally
docker compose up -d --scale backend=3

# Scale workers
docker compose --profile workers up -d --scale worker=5

# Check scaled services
docker compose ps
```

## Building and Updating

```bash
# Build images
./scripts/deploy.sh build

# Build specific service
docker compose build backend

# Pull latest images
docker compose pull

# Update and restart
docker compose up -d --no-deps --build backend
```

## Development Mode

```bash
# Start with development overrides
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Enable hot reload
# Source code is mounted, changes reflect immediately
```

## Production Mode

```bash
# Start with production settings
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --profile frontend --profile workers --profile nginx up -d

# Check resource usage
docker stats

# View production logs
docker compose logs -f --tail=100
```

## Cleanup

```bash
# Stop and remove containers (keeps volumes)
./scripts/deploy.sh down

# Remove everything including volumes (DATA LOSS!)
./scripts/deploy.sh clean

# Remove unused images
docker image prune -a

# Full system cleanup
docker system prune -a --volumes
```

## Troubleshooting

```bash
# Check configuration
docker compose config

# Verify environment variables
docker compose config | grep -A 5 environment

# Check container health
docker inspect tradingagents-backend | grep -A 10 Health

# View container details
docker inspect tradingagents-backend

# Check network connectivity
docker compose exec backend ping postgres
docker compose exec backend nc -zv redis 6379

# Restart stuck container
docker compose restart backend

# View last 50 log lines
docker compose logs --tail=50 backend
```

## API Testing

```bash
# Health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs

# Create session
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "NVDA",
    "date": "2024-05-10",
    "config": {
      "deep_think_llm": "o4-mini",
      "quick_think_llm": "gpt-4o-mini"
    }
  }'

# Stream events (replace SESSION_ID)
curl -N http://localhost:8000/sessions/SESSION_ID/events
```

## Common Issues

### Services won't start
```bash
# Check logs
./scripts/deploy.sh logs

# Verify disk space
df -h

# Check Docker is running
docker ps
```

### Database connection errors
```bash
# Check PostgreSQL is running
docker compose ps postgres

# Test connection
docker compose exec postgres pg_isready -U tradingagents

# Restart database
docker compose restart postgres
```

### Redis connection errors
```bash
# Check Redis is running
docker compose ps redis

# Test connection
docker compose exec redis redis-cli ping

# Restart Redis
docker compose restart redis
```

### Port conflicts
```bash
# Check what's using the port
lsof -i :8000

# Change port in .env
# BACKEND_PORT=8001
```

### Out of memory
```bash
# Check memory usage
docker stats

# Reduce workers
WORKER_CONCURRENCY=2 docker compose up -d

# Increase Docker memory (Docker Desktop)
# Settings > Resources > Memory
```

## Makefile Shortcuts

```bash
make docker-build    # Build images
make docker-up       # Start services
make docker-down     # Stop services
make docker-logs     # View logs
make docker-health   # Health check
make docker-migrate  # Run migrations
```

## Environment Variables

### Required
```env
OPENAI_API_KEY=your_key
ALPHA_VANTAGE_API_KEY=your_key
POSTGRES_PASSWORD=secure_password
REDIS_PASSWORD=secure_password
```

### Common Settings
```env
DEBUG=false
BACKEND_PORT=8000
FRONTEND_PORT=3000
WORKER_CONCURRENCY=4
AUTO_START_WORKERS=true
```

## Service URLs

- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics
- **Frontend**: http://localhost:3000 (if enabled)
- **Nginx**: http://localhost:80 (if enabled)

## Docker Compose Profiles

- **Default**: backend, postgres, redis
- **workers**: Add background workers
- **frontend**: Add Next.js UI
- **nginx**: Add reverse proxy

## Files and Directories

```
.
├── docker-compose.yml           # Main compose file
├── docker-compose.dev.yml       # Development overrides
├── docker-compose.prod.yml      # Production overrides
├── .env.docker                  # Environment template
├── scripts/
│   ├── deploy.sh               # Deployment script
│   ├── healthcheck.sh          # Health check script
│   └── init-db.sql             # Database init
├── nginx/
│   └── nginx.conf              # Nginx configuration
└── packages/
    ├── backend/
    │   ├── Dockerfile          # Backend image
    │   └── scripts/
    │       └── entrypoint.sh   # Container startup
    └── frontend/
        └── Dockerfile          # Frontend image
```

## Documentation

- **Quick Start**: [DOCKER_QUICKSTART.md](./DOCKER_QUICKSTART.md)
- **Full Guide**: [DEPLOYMENT.md](./DEPLOYMENT.md)
- **Checklist**: [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)
- **Summary**: [DOCKER_DEPLOYMENT_SUMMARY.md](./DOCKER_DEPLOYMENT_SUMMARY.md)
- **Operations**: [docs/operations/README.md](./docs/operations/README.md)

## Support

- **Discord**: https://discord.com/invite/hk9PGKShPK
- **GitHub**: https://github.com/TauricResearch/TradingAgents
- **Issues**: https://github.com/TauricResearch/TradingAgents/issues

---

**Pro Tip**: Bookmark this page for quick reference! 📚
