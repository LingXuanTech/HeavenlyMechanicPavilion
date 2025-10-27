#!/bin/bash
set -e

echo "=== TradingAgents Backend Entrypoint ==="

# Function to wait for a service
wait_for_service() {
  local host=$1
  local port=$2
  local service_name=$3
  local max_retries=30
  local count=0
  
  echo "Waiting for $service_name..."
  until nc -z "$host" "$port" 2>/dev/null; do
    count=$((count + 1))
    if [ $count -ge $max_retries ]; then
      echo "$service_name did not become ready in time"
      exit 1
    fi
    echo "$service_name is unavailable - sleeping"
    sleep 2
  done
  echo "$service_name is up and running!"
}

# Wait for PostgreSQL to be ready
wait_for_service "postgres" "5432" "PostgreSQL"

# Wait for Redis to be ready (if enabled)
if [ "${REDIS_ENABLED}" = "true" ]; then
  wait_for_service "redis" "6379" "Redis"
fi

# Run database migrations
echo "Running database migrations..."
cd /app
alembic upgrade head || {
  echo "Migration failed, but continuing..."
}

# Create results directory if it doesn't exist
mkdir -p /app/results /app/data
echo "Results directory ready: /app/results"

echo "=== Starting Application ==="
# Execute the command passed to the entrypoint
exec "$@"
