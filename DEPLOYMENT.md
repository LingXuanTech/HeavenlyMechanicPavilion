# TradingAgents Deployment Guide

This guide provides comprehensive instructions for deploying TradingAgents using Docker and Docker Compose.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Production Deployment](#production-deployment)
- [Scaling Services](#scaling-services)
- [Reverse Proxy and WebSocket Configuration](#reverse-proxy-and-websocket-configuration)
- [Monitoring and Logging](#monitoring-and-logging)
- [Backup and Restore](#backup-and-restore)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- Docker Engine 20.10+ and Docker Compose V2
- At least 4GB RAM (8GB+ recommended for production)
- 20GB disk space minimum
- API keys for OpenAI and Alpha Vantage

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/TauricResearch/TradingAgents.git
cd TradingAgents
```

### 2. Configure Environment

```bash
# Copy the Docker environment template
cp .env.docker .env

# Edit the .env file with your configuration
# At minimum, update:
# - OPENAI_API_KEY
# - ALPHA_VANTAGE_API_KEY
# - POSTGRES_PASSWORD
# - REDIS_PASSWORD
nano .env
```

### 3. Start Services

```bash
# Start core services (backend, postgres, redis)
./scripts/deploy.sh up

# Or with frontend
PROFILE=frontend ./scripts/deploy.sh up

# Or with all services including workers
PROFILE=workers,frontend ./scripts/deploy.sh up
```

### 4. Verify Deployment

```bash
# Check service status
./scripts/deploy.sh ps

# View logs
./scripts/deploy.sh logs

# Check backend health
curl http://localhost:8000/health
```

## Configuration

### Environment Variables

The `.env` file controls all service configurations. Key sections:

#### Required API Keys
```env
OPENAI_API_KEY=your_key_here
ALPHA_VANTAGE_API_KEY=your_key_here
```

#### Database Configuration
```env
POSTGRES_DB=tradingagents
POSTGRES_USER=tradingagents
POSTGRES_PASSWORD=secure_password_here
```

#### Redis Configuration
```env
REDIS_ENABLED=true
REDIS_PASSWORD=secure_password_here
REDIS_MAX_MEMORY=256mb
```

#### TradingAgents Settings
```env
TRADINGAGENTS_LLM_PROVIDER=openai
TRADINGAGENTS_DEEP_THINK_LLM=o4-mini
TRADINGAGENTS_QUICK_THINK_LLM=gpt-4o-mini
```

### Service Profiles

Docker Compose profiles allow selective service deployment:

- **Default**: Backend, PostgreSQL, Redis (no profile needed)
- **workers**: Add background worker service
- **frontend**: Add Next.js frontend
- **nginx**: Add Nginx reverse proxy

```bash
# Start with specific profiles
PROFILE=workers,frontend ./scripts/deploy.sh up

# Or using docker compose directly
docker compose --profile workers --profile frontend up -d
```

## Production Deployment

### 1. Security Hardening

#### Update Default Passwords
```bash
# Generate secure passwords
openssl rand -base64 32  # For POSTGRES_PASSWORD
openssl rand -base64 32  # For REDIS_PASSWORD
```

#### Use Secrets Management
For production, use Docker secrets or external secret managers:

```yaml
# docker-compose.prod.yml
secrets:
  postgres_password:
    external: true
  redis_password:
    external: true
```

### 2. SSL/TLS Configuration

#### Generate SSL Certificates

```bash
# Using Let's Encrypt (recommended)
certbot certonly --standalone -d your-domain.com

# Or self-signed for testing
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem
```

#### Update Nginx Configuration

Edit `nginx/nginx.conf` and uncomment the HTTPS server block, then:

```bash
# Restart with nginx profile
PROFILE=nginx,frontend ./scripts/deploy.sh restart
```

### 3. Database Migrations

Always run migrations before deploying new versions:

```bash
# Run migrations
./scripts/deploy.sh migrate

# Or manually
docker compose exec backend alembic upgrade head

# Check migration status
docker compose exec backend alembic current
```

### 4. Production Environment Settings

```env
DEBUG=false
DATABASE_ECHO=false
AUTO_START_WORKERS=true
MONITORING_ENABLED=true
METRICS_ENABLED=true
```

## Scaling Services

### Horizontal Scaling

#### Scale Backend API

```bash
# Scale backend to 3 replicas
docker compose up -d --scale backend=3

# Update nginx upstream for load balancing
# Add multiple backend servers to nginx/nginx.conf:
upstream backend {
    least_conn;
    server backend_1:8000;
    server backend_2:8000;
    server backend_3:8000;
}
```

#### Scale Workers

```bash
# Scale workers to handle more concurrent tasks
docker compose --profile workers up -d --scale worker=5

# Adjust worker concurrency
WORKER_CONCURRENCY=8 docker compose --profile workers up -d
```

### Vertical Scaling

Update resource limits in docker-compose.yml:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

### Database Scaling

For production workloads:

```yaml
postgres:
  command: postgres -c max_connections=200 -c shared_buffers=256MB
  deploy:
    resources:
      limits:
        memory: 2G
```

## Reverse Proxy and WebSocket Configuration

### Nginx Configuration

The included `nginx/nginx.conf` provides:

1. **Load Balancing**: Distributes requests across backend instances
2. **WebSocket Support**: Handles upgrade headers properly
3. **SSE Support**: Configured for Server-Sent Events
4. **Rate Limiting**: Protects against abuse

#### WebSocket Specifics

WebSocket connections require special handling:

```nginx
location /sessions/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    
    # Long timeouts for WebSocket
    proxy_connect_timeout 7d;
    proxy_send_timeout 7d;
    proxy_read_timeout 7d;
}
```

#### SSE (Server-Sent Events) Configuration

```nginx
location /sessions {
    proxy_pass http://backend;
    
    # Disable buffering for SSE
    proxy_buffering off;
    proxy_cache off;
    proxy_set_header Connection '';
    chunked_transfer_encoding off;
}
```

### Traefik Alternative

For Traefik users, create `docker-compose.traefik.yml`:

```yaml
services:
  backend:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.backend.rule=PathPrefix(`/api`) || PathPrefix(`/sessions`)"
      - "traefik.http.services.backend.loadbalancer.server.port=8000"
      
  frontend:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.frontend.rule=PathPrefix(`/`)"
      - "traefik.http.services.frontend.loadbalancer.server.port=3000"
```

## Monitoring and Logging

### Log Management

```bash
# View all logs
./scripts/deploy.sh logs

# View specific service logs
./scripts/deploy.sh logs backend

# Follow logs in real-time
docker compose logs -f backend

# Export logs
docker compose logs > tradingagents.log
```

### Metrics Collection

The backend exposes Prometheus metrics when `METRICS_ENABLED=true`:

```bash
# Access metrics endpoint
curl http://localhost:8000/metrics
```

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Check all containers
docker compose ps
```

### Container Stats

```bash
# Real-time resource usage
docker stats

# Specific container
docker stats tradingagents-backend
```

## Backup and Restore

### Database Backup

```bash
# Create backup
docker compose exec postgres pg_dump -U tradingagents tradingagents > backup.sql

# Or use a volume backup
docker run --rm \
  -v tradingagents_postgres_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/postgres-backup.tar.gz /data
```

### Database Restore

```bash
# Restore from SQL dump
docker compose exec -T postgres psql -U tradingagents tradingagents < backup.sql

# Or restore volume
docker run --rm \
  -v tradingagents_postgres_data:/data \
  -v $(pwd):/backup \
  alpine sh -c "cd / && tar xzf /backup/postgres-backup.tar.gz"
```

### Redis Backup

```bash
# Trigger Redis save
docker compose exec redis redis-cli -a $REDIS_PASSWORD SAVE

# Copy RDB file
docker cp tradingagents-redis:/data/dump.rdb redis-backup.rdb
```

## Troubleshooting

### Common Issues

#### Services Won't Start

```bash
# Check logs for errors
./scripts/deploy.sh logs

# Verify environment variables
docker compose config

# Check disk space
df -h
```

#### Database Connection Issues

```bash
# Check PostgreSQL is healthy
docker compose ps postgres

# Test connection
docker compose exec postgres psql -U tradingagents -d tradingagents -c "SELECT 1;"

# Check connection from backend
docker compose exec backend python -c "from app.db import get_db_manager; import asyncio; asyncio.run(get_db_manager().ping())"
```

#### Redis Connection Issues

```bash
# Check Redis is healthy
docker compose ps redis

# Test connection
docker compose exec redis redis-cli -a $REDIS_PASSWORD ping
```

#### Migration Failures

```bash
# Check migration status
docker compose exec backend alembic current

# View migration history
docker compose exec backend alembic history

# Downgrade if needed
docker compose exec backend alembic downgrade -1
```

#### Out of Memory

```bash
# Check container memory usage
docker stats

# Increase Docker memory limits
# Docker Desktop: Settings > Resources > Memory

# Reduce worker concurrency
WORKER_CONCURRENCY=2 docker compose up -d
```

#### High CPU Usage

```bash
# Check which process is consuming CPU
docker exec tradingagents-backend top

# Reduce number of workers
docker compose up -d --scale worker=1

# Adjust LLM rate limiting in config
```

### Performance Tuning

#### Database Performance

```yaml
postgres:
  command: |
    postgres
    -c shared_buffers=512MB
    -c effective_cache_size=1GB
    -c maintenance_work_mem=128MB
    -c max_connections=100
```

#### Redis Performance

```yaml
redis:
  command: |
    redis-server
    --maxmemory 512mb
    --maxmemory-policy allkeys-lru
    --save ""
```

### Getting Help

1. Check logs: `./scripts/deploy.sh logs`
2. Review configuration: `docker compose config`
3. Inspect containers: `docker compose ps -a`
4. Join the [Discord community](https://discord.com/invite/hk9PGKShPK)
5. Open an issue on [GitHub](https://github.com/TauricResearch/TradingAgents/issues)

## Advanced Topics

### Custom Docker Networks

```yaml
networks:
  tradingagents-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### External Services

To use external PostgreSQL or Redis:

```yaml
services:
  backend:
    environment:
      DATABASE_URL: postgresql+asyncpg://user:pass@external-db:5432/tradingagents
      REDIS_HOST: external-redis
```

### Multi-Node Deployment

For production clusters, consider:

1. **Docker Swarm**: Built-in orchestration
2. **Kubernetes**: More features, complex setup
3. **Managed Services**: AWS ECS, Google Cloud Run, etc.

### CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to production
        run: |
          ./scripts/deploy.sh build
          ./scripts/deploy.sh up
```

## Security Best Practices

1. **Never commit `.env` files** to version control
2. **Use strong passwords** for all services
3. **Enable SSL/TLS** in production
4. **Regular updates**: Keep Docker images up to date
5. **Network isolation**: Use internal networks where possible
6. **Limit exposure**: Only expose necessary ports
7. **Resource limits**: Set memory and CPU limits
8. **Security scanning**: Use tools like Trivy or Snyk

## Production Checklist

Before deploying to production:

- [ ] Update all default passwords
- [ ] Configure SSL/TLS certificates
- [ ] Set `DEBUG=false`
- [ ] Configure backup strategy
- [ ] Set up monitoring and alerting
- [ ] Test disaster recovery procedures
- [ ] Configure log aggregation
- [ ] Review resource limits
- [ ] Enable rate limiting
- [ ] Document runbook procedures
- [ ] Test scaling procedures
- [ ] Configure health checks
- [ ] Review security settings
