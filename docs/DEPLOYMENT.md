# Deployment Guide

This guide consolidates all deployment scenarios for TradingAgents: rapid Docker-based setups, production hardening, scaling strategies, monitoring hooks, and operational runbooks.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (Docker Compose)](#quick-start-docker-compose)
3. [Service Profiles](#service-profiles)
4. [Managing the Stack](#managing-the-stack)
5. [Production Hardening](#production-hardening)
6. [Scaling Strategies](#scaling-strategies)
7. [Monitoring & Observability](#monitoring--observability)
8. [Backup & Recovery](#backup--recovery)
9. [Troubleshooting](#troubleshooting)
10. [Deployment Checklist](#deployment-checklist)
11. [Further Reading](#further-reading)

## Prerequisites

- Docker Engine 20.10+
- Docker Compose V2
- At least 4 CPU cores, 8 GB RAM, and 20 GB free disk space recommended
- API keys for OpenAI and Alpha Vantage (plus optional providers)
- Executable scripts: `chmod +x scripts/*.sh`

## Quick Start (Docker Compose)

1. **Clone & configure**

   ```bash
   git clone https://github.com/TauricResearch/TradingAgents.git
   cd TradingAgents

   cp .env.docker .env
   # Edit .env with your API keys and secure passwords
   ```

   Minimum variables to update:

   ```env
   OPENAI_API_KEY=sk-your-openai-key
   ALPHA_VANTAGE_API_KEY=your-alpha-vantage-key
   POSTGRES_PASSWORD=choose-a-secure-password
   REDIS_PASSWORD=choose-a-secure-password
   ```

2. **Start services**

   ```bash
   ./scripts/deploy.sh up
   ```

   By default this runs the backend API, PostgreSQL, and Redis.

3. **Verify health**

   ```bash
   ./scripts/healthcheck.sh
   curl http://localhost:8000/health
   ./scripts/deploy.sh logs -f backend
   ```

4. **Access components**

   - Backend API: [http://localhost:8000](http://localhost:8000)
   - API documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Frontend Control Center (when enabled): [http://localhost:3000](http://localhost:3000)

## Service Profiles

Docker Compose profiles allow you to pick the services you need:

| Profile | Services Enabled |
| --- | --- |
| *(default)* | Backend, PostgreSQL, Redis |
| `frontend` | Adds Next.js Control Center |
| `workers` | Adds background workers for streaming/data refresh |
| `nginx` | Adds nginx reverse proxy with SSL/WebSocket support |

Examples:

```bash
PROFILE=frontend ./scripts/deploy.sh up
PROFILE=frontend,workers ./scripts/deploy.sh up
PROFILE=frontend,workers,nginx ./scripts/deploy.sh up
```

## Managing the Stack

Common commands (`scripts/deploy.sh` wraps `docker compose`):

```bash
./scripts/deploy.sh up             # Start selected services
./scripts/deploy.sh down           # Stop services (retain volumes)
./scripts/deploy.sh logs [svc]     # View logs (optionally follow with -f)
./scripts/deploy.sh ps             # Service status
./scripts/deploy.sh restart        # Restart services
./scripts/deploy.sh build          # Build/rebuild images
./scripts/deploy.sh migrate        # Run database migrations
./scripts/deploy.sh shell backend  # Shell into a container
./scripts/deploy.sh clean          # Tear down and remove volumes (DATA LOSS)
```

Plain docker compose equivalents:

```bash
docker compose up -d
docker compose --profile frontend up -d
```

## Production Hardening

### Security

- Generate strong passwords for PostgreSQL, Redis, and any exposed services (`openssl rand -base64 32`).
- Use Docker secrets or a secrets manager (`secrets.example.yml` provides templates).
- Terminate TLS using the nginx profile or an upstream load balancer.
- Restrict exposed ports using firewalls or security groups.
- Regularly update base images and rebuild (`./scripts/deploy.sh build`).

### SSL/TLS

For nginx-based SSL termination:

```bash
mkdir -p nginx/ssl
# Example self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem

PROFILE=nginx,frontend ./scripts/deploy.sh restart
```

Update `nginx/nginx.conf` with certificate paths and desired cipher suites.

### Configuration Management

- Set `DEBUG=false`, `DATABASE_ECHO=false`, `MONITORING_ENABLED=true`, and `METRICS_ENABLED=true` in production.
- Place vendor configuration (`vendor_config.yaml`) and `.env` files outside version control. Mount or inject them at runtime.
- Maintain separate `.env` files per environment (dev/staging/prod).

## Scaling Strategies

### Horizontal Scaling

```bash
# Spawn additional backend replicas
docker compose up -d --scale backend=3

# Scale workers
docker compose --profile workers up -d --scale worker=5
```

Update nginx upstream blocks to load-balance across backend replicas. For WebSockets/SSE ensure sticky sessions or least-connection balancing.

### Vertical Scaling

Configure resource limits in `docker-compose.prod.yml`:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 4G
        reservations:
          cpus: "1"
          memory: 2G
```

### Kubernetes & Cloud

Reference [`docs/operations/kubernetes-example.md`](./operations/kubernetes-example.md) for manifests covering Deployments, Services, Ingress, ConfigMaps, Secrets, and autoscaling hints. Adapt them to your chosen cloud provider or managed Kubernetes platform.

## Monitoring & Observability

- **Prometheus**: Scrape `/monitoring/metrics` from the backend, optionally via nginx.
- **Alerting**: Enable email/webhook alerts via environment variables. Test with `POST /monitoring/alerts/test`.
- **Logging**: Aggregate container logs using `docker compose logs --tail=100 -f`, or forward to ELK/Datadog.
- **Health Checks**: Automate `./scripts/healthcheck.sh` or query `/monitoring/health` in your uptime tooling.
- **Frontend Dashboard**: The Control Center’s `/monitoring` route visualises system health and recent alerts.

## Backup & Recovery

### PostgreSQL

```bash
# Ad-hoc backup
docker compose exec postgres pg_dump -U tradingagents tradingagents > backup.sql

# Restore
cat backup.sql | docker compose exec -T postgres psql -U tradingagents tradingagents
```

For volume-level backups:

```bash
docker run --rm -v tradingagents_postgres_data:/data -v $(pwd):/backup alpine \
  tar czf /backup/postgres-backup.tar.gz /data
```

### Redis

```bash
# Trigger snapshot
docker compose exec redis redis-cli -a $REDIS_PASSWORD SAVE

# Copy RDB file
docker cp tradingagents-redis:/data/dump.rdb redis-backup.rdb
```

### Disaster Recovery Checklist

- Backups stored off-site with retention policy
- Tested restore procedure
- Documented rollback plan (compose tags, migrations)

## Troubleshooting

| Symptom | Checks |
| --- | --- |
| Services won’t start | `./scripts/deploy.sh logs`, `docker compose ps`, verify `.env` values |
| Port conflicts | `lsof -i :8000`, adjust `BACKEND_PORT` / `FRONTEND_PORT` in `.env` |
| Migration failures | `docker compose exec backend alembic current`, inspect logs |
| Redis connection errors | Ensure `REDIS_ENABLED=true`, validate password, `docker compose ps redis` |
| High latency | Monitor `/monitoring/metrics`, scale workers/backends, enable caching |
| Out-of-memory | `docker stats`, reduce worker concurrency, raise resource limits |

Useful commands:

```bash
./scripts/deploy.sh logs backend          # Tail backend logs
./scripts/deploy.sh shell backend         # Debug inside container
./scripts/deploy.sh migrate               # Apply pending migrations
docker compose config                     # Validate compose config
docker stats                              # Real-time resource usage
```

## Deployment Checklist

- [ ] `.env` configured with secure credentials and production flags
- [ ] Docker images built (`./scripts/deploy.sh build`)
- [ ] Database migrations applied (`./scripts/deploy.sh migrate`)
- [ ] Health checks succeed (`./scripts/healthcheck.sh` and `/monitoring/health`)
- [ ] TLS configured (nginx or external load balancer)
- [ ] Monitoring/alerting enabled and tested
- [ ] Backups scheduled and restore tested
- [ ] Scaling (horizontal/vertical) validated under load
- [ ] Runbook and escalation paths documented

Capture environment-specific notes in your own runbooks or ticketing system so operational knowledge remains current.

## Further Reading

- [Architecture Overview](./ARCHITECTURE.md) – Subsystem design details.
- [API Reference](./API.md) – Endpoints for automation and integration.
- [Configuration Guide](./CONFIGURATION.md) – Tunable environment variables and vendor routing.
- [Operations Guides](./operations/README.md) – Supplemental runbooks and Kubernetes manifests.

Need help? Reach out via [Discord](https://discord.com/invite/hk9PGKShPK) or [GitHub Issues](https://github.com/TauricResearch/TradingAgents/issues).
