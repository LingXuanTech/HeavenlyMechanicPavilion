.PHONY: sync lint format run cli docker-build docker-up docker-down docker-logs docker-health

sync:
	pnpm run sync

lint:
	pnpm run lint

format:
	pnpm run format

run:
	pnpm run run

cli:
	pnpm run cli

# Docker commands
docker-build:
	./scripts/deploy.sh build

docker-up:
	./scripts/deploy.sh up

docker-down:
	./scripts/deploy.sh down

docker-logs:
	./scripts/deploy.sh logs

docker-health:
	./scripts/healthcheck.sh

docker-migrate:
	./scripts/deploy.sh migrate
