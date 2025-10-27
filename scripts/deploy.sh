#!/bin/bash
# TradingAgents Deployment Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
ENV_FILE="${ENV_FILE:-.env}"
PROFILE="${PROFILE:-}"

echo -e "${GREEN}=== TradingAgents Deployment Script ===${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

# Check if Docker Compose is available
if ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not available${NC}"
    exit 1
fi

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}Warning: $ENV_FILE not found. Creating from template...${NC}"
    if [ -f ".env.docker" ]; then
        cp .env.docker "$ENV_FILE"
        echo -e "${YELLOW}Please edit $ENV_FILE with your configuration before continuing${NC}"
        exit 1
    else
        echo -e "${RED}Error: No template file found${NC}"
        exit 1
    fi
fi

# Check for required environment variables
source "$ENV_FILE"
REQUIRED_VARS=("OPENAI_API_KEY" "POSTGRES_PASSWORD" "REDIS_PASSWORD")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ] || [ "${!var}" = "your_"* ] || [ "${!var}" = "changeme"* ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo -e "${RED}Error: The following required variables are not set or have default values:${NC}"
    printf '%s\n' "${MISSING_VARS[@]}"
    echo -e "${YELLOW}Please update your $ENV_FILE file${NC}"
    exit 1
fi

# Parse command line arguments
ACTION="${1:-up}"
PROFILES=""

if [ -n "$PROFILE" ]; then
    PROFILES="--profile $PROFILE"
fi

# Handle different actions
case $ACTION in
    up)
        echo -e "${GREEN}Starting TradingAgents services...${NC}"
        docker compose -f "$COMPOSE_FILE" $PROFILES up -d
        echo -e "${GREEN}Services started successfully!${NC}"
        echo ""
        echo "Access the services at:"
        echo "  - Backend API: http://localhost:${BACKEND_PORT:-8000}"
        echo "  - Frontend: http://localhost:${FRONTEND_PORT:-3000}"
        ;;
    
    down)
        echo -e "${YELLOW}Stopping TradingAgents services...${NC}"
        docker compose -f "$COMPOSE_FILE" down
        echo -e "${GREEN}Services stopped${NC}"
        ;;
    
    restart)
        echo -e "${YELLOW}Restarting TradingAgents services...${NC}"
        docker compose -f "$COMPOSE_FILE" $PROFILES restart
        echo -e "${GREEN}Services restarted${NC}"
        ;;
    
    build)
        echo -e "${GREEN}Building TradingAgents images...${NC}"
        docker compose -f "$COMPOSE_FILE" build --no-cache
        echo -e "${GREEN}Build complete${NC}"
        ;;
    
    logs)
        SERVICE="${2:-}"
        if [ -n "$SERVICE" ]; then
            docker compose -f "$COMPOSE_FILE" logs -f "$SERVICE"
        else
            docker compose -f "$COMPOSE_FILE" logs -f
        fi
        ;;
    
    ps)
        docker compose -f "$COMPOSE_FILE" ps
        ;;
    
    clean)
        echo -e "${RED}This will remove all containers, volumes, and images. Are you sure? (y/N)${NC}"
        read -r response
        if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
            docker compose -f "$COMPOSE_FILE" down -v --remove-orphans
            echo -e "${GREEN}Cleanup complete${NC}"
        else
            echo "Cancelled"
        fi
        ;;
    
    migrate)
        echo -e "${GREEN}Running database migrations...${NC}"
        docker compose -f "$COMPOSE_FILE" exec backend alembic upgrade head
        echo -e "${GREEN}Migrations complete${NC}"
        ;;
    
    shell)
        SERVICE="${2:-backend}"
        echo -e "${GREEN}Opening shell in $SERVICE container...${NC}"
        docker compose -f "$COMPOSE_FILE" exec "$SERVICE" /bin/sh
        ;;
    
    *)
        echo "Usage: $0 {up|down|restart|build|logs|ps|clean|migrate|shell} [service]"
        echo ""
        echo "Commands:"
        echo "  up       - Start all services"
        echo "  down     - Stop all services"
        echo "  restart  - Restart all services"
        echo "  build    - Build all images"
        echo "  logs     - View logs (optionally specify service)"
        echo "  ps       - List running services"
        echo "  clean    - Remove all containers, volumes, and images"
        echo "  migrate  - Run database migrations"
        echo "  shell    - Open shell in container (default: backend)"
        echo ""
        echo "Environment Variables:"
        echo "  COMPOSE_FILE - Docker Compose file to use (default: docker-compose.yml)"
        echo "  ENV_FILE     - Environment file to use (default: .env)"
        echo "  PROFILE      - Docker Compose profile to use (e.g., workers, frontend, nginx)"
        exit 1
        ;;
esac
