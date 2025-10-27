#!/bin/bash
# Health Check Script for TradingAgents Services

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
TIMEOUT=5

echo -e "${BLUE}=== TradingAgents Health Check ===${NC}\n"

# Check if services are running
echo -e "${BLUE}Checking service status...${NC}"
docker compose ps

echo ""

# Function to check endpoint
check_endpoint() {
    local name=$1
    local url=$2
    local expected_status=${3:-200}
    
    echo -n "Checking $name... "
    
    if response=$(curl -s -w "%{http_code}" -o /dev/null --max-time $TIMEOUT "$url" 2>/dev/null); then
        if [ "$response" = "$expected_status" ]; then
            echo -e "${GREEN}✓ OK${NC} (HTTP $response)"
            return 0
        else
            echo -e "${YELLOW}⚠ WARNING${NC} (HTTP $response, expected $expected_status)"
            return 1
        fi
    else
        echo -e "${RED}✗ FAILED${NC} (No response)"
        return 1
    fi
}

# Check PostgreSQL
echo -n "Checking PostgreSQL... "
if docker compose exec -T postgres pg_isready -U tradingagents > /dev/null 2>&1; then
    echo -e "${GREEN}✓ OK${NC}"
else
    echo -e "${RED}✗ FAILED${NC}"
fi

# Check Redis
echo -n "Checking Redis... "
if docker compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ OK${NC}"
else
    echo -e "${RED}✗ FAILED${NC}"
fi

# Check Backend
check_endpoint "Backend Root" "$BACKEND_URL/"
check_endpoint "Backend Health" "$BACKEND_URL/health"

# Check if backend can connect to database
echo -n "Checking Backend → PostgreSQL... "
if response=$(curl -s "$BACKEND_URL/" 2>/dev/null); then
    if echo "$response" | grep -q "connected"; then
        echo -e "${GREEN}✓ OK${NC}"
    else
        echo -e "${YELLOW}⚠ WARNING${NC}"
    fi
else
    echo -e "${RED}✗ FAILED${NC}"
fi

# Check if backend can connect to Redis
echo -n "Checking Backend → Redis... "
if response=$(curl -s "$BACKEND_URL/" 2>/dev/null); then
    if echo "$response" | grep -q "enabled"; then
        echo -e "${GREEN}✓ OK${NC}"
    else
        echo -e "${YELLOW}⚠ Redis disabled${NC}"
    fi
else
    echo -e "${RED}✗ FAILED${NC}"
fi

# Check Frontend (if enabled)
if docker compose ps frontend | grep -q "Up"; then
    check_endpoint "Frontend" "$FRONTEND_URL"
else
    echo "Frontend: ${YELLOW}Not deployed${NC}"
fi

# Check Nginx (if enabled)
if docker compose ps nginx | grep -q "Up"; then
    check_endpoint "Nginx" "http://localhost:80"
else
    echo "Nginx: ${YELLOW}Not deployed${NC}"
fi

# Check Workers (if enabled)
echo -n "Checking Workers... "
if docker compose ps worker | grep -q "Up"; then
    worker_count=$(docker compose ps worker | grep -c "Up" || true)
    echo -e "${GREEN}✓ OK${NC} ($worker_count worker(s) running)"
else
    echo "${YELLOW}Not deployed${NC}"
fi

echo ""
echo -e "${BLUE}=== Resource Usage ===${NC}"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep tradingagents || true

echo ""
echo -e "${BLUE}=== Disk Usage ===${NC}"
docker system df

echo ""
echo -e "${GREEN}Health check complete!${NC}"
