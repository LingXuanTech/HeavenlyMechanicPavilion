# Docker Quick Start Guide

Get TradingAgents up and running with Docker in minutes.

## Prerequisites

- Docker Engine 20.10+ installed
- Docker Compose V2 installed
- OpenAI API key
- Alpha Vantage API key (free tier available)

## 5-Minute Setup

### Step 1: Get API Keys

1. **OpenAI**: Get your API key from https://platform.openai.com/api-keys
2. **Alpha Vantage**: Get a free key from https://www.alphavantage.co/support/#api-key

### Step 2: Configure Environment

```bash
# Clone the repository (if you haven't already)
git clone https://github.com/TauricResearch/TradingAgents.git
cd TradingAgents

# Copy the Docker environment template
cp .env.docker .env

# Edit the .env file
nano .env  # or use your preferred editor
```

**Minimum required changes in `.env`:**
```env
OPENAI_API_KEY=sk-your-actual-openai-key-here
ALPHA_VANTAGE_API_KEY=your-alpha-vantage-key-here
POSTGRES_PASSWORD=choose-a-secure-password
REDIS_PASSWORD=choose-a-secure-password
```

### Step 3: Start Services

```bash
# Start backend, PostgreSQL, and Redis
./scripts/deploy.sh up

# Wait for services to start (about 30 seconds)
# Watch the logs
./scripts/deploy.sh logs -f
```

### Step 4: Verify Installation

```bash
# Check service health
./scripts/healthcheck.sh

# Or manually check the backend
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "enabled"
}
```

## What's Running?

After successful deployment, you'll have:

- **Backend API**: http://localhost:8000
  - API Documentation: http://localhost:8000/docs
  - Health Check: http://localhost:8000/health
  
- **PostgreSQL**: localhost:5432
  - Database: tradingagents
  - User: tradingagents
  
- **Redis**: localhost:6379
  - Used for caching and streaming

## Using the API

### Start a Trading Session

```bash
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
```

### Stream Session Events (SSE)

```bash
# Replace SESSION_ID with the ID from the POST response
curl -N http://localhost:8000/sessions/SESSION_ID/events
```

## Optional Services

### Add Frontend (Control Center)

```bash
# Stop existing services
./scripts/deploy.sh down

# Start with frontend
PROFILE=frontend ./scripts/deploy.sh up
```

Access the frontend at: http://localhost:3000

### Add Background Workers

```bash
# Start with workers for background processing
PROFILE=workers ./scripts/deploy.sh up
```

### Add Everything

```bash
# Start all services including frontend, workers, and nginx
PROFILE=frontend,workers,nginx ./scripts/deploy.sh up
```

With nginx, access everything through:
- http://localhost:80 (Frontend)
- http://localhost:80/api (Backend API)

## Common Commands

```bash
# View logs
./scripts/deploy.sh logs

# View logs for specific service
./scripts/deploy.sh logs backend

# Check service status
./scripts/deploy.sh ps

# Stop all services
./scripts/deploy.sh down

# Restart services
./scripts/deploy.sh restart

# Run database migrations
./scripts/deploy.sh migrate

# Open shell in backend container
./scripts/deploy.sh shell backend

# Clean up everything (removes all data!)
./scripts/deploy.sh clean
```

## Using Make

If you prefer make commands:

```bash
make docker-up       # Start services
make docker-down     # Stop services
make docker-logs     # View logs
make docker-health   # Health check
make docker-migrate  # Run migrations
```

## Troubleshooting

### Services won't start

```bash
# Check Docker is running
docker ps

# Check logs for errors
./scripts/deploy.sh logs

# Verify environment variables
docker compose config
```

### "Connection refused" errors

Wait 30-60 seconds for all services to fully start, then try again.

```bash
# Watch startup progress
./scripts/deploy.sh logs -f backend
```

### Database migration errors

```bash
# Run migrations manually
./scripts/deploy.sh migrate

# Or reset database (WARNING: deletes all data)
./scripts/deploy.sh down -v
./scripts/deploy.sh up
```

### Out of memory

```bash
# Check Docker memory allocation
docker stats

# Increase Docker memory in Docker Desktop:
# Settings > Resources > Memory (recommend 8GB+)
```

### Port already in use

Edit `.env` and change the port:

```env
BACKEND_PORT=8001   # Change from 8000
FRONTEND_PORT=3001  # Change from 3000
```

## Development Mode

For development with hot-reload:

```bash
# Use development compose file
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

This enables:
- Hot-reload for both frontend and backend
- Debug mode
- Verbose logging
- Source code mounting

## Next Steps

1. **Read the Full Guide**: See [DEPLOYMENT.md](./DEPLOYMENT.md) for production deployment
2. **API Documentation**: Visit http://localhost:8000/docs for interactive API docs
3. **Run the CLI**: See main [README.md](./README.md) for CLI usage
4. **Customize Configuration**: Edit `.env` for advanced options

## Getting Help

- Check logs: `./scripts/deploy.sh logs`
- Run health check: `./scripts/healthcheck.sh`
- Join our [Discord](https://discord.com/invite/hk9PGKShPK)
- Open an issue on [GitHub](https://github.com/TauricResearch/TradingAgents/issues)

## Stopping and Cleaning Up

```bash
# Stop services (keeps data)
./scripts/deploy.sh down

# Stop and remove volumes (deletes all data!)
./scripts/deploy.sh clean
```

---

**Happy Trading! 🚀**
