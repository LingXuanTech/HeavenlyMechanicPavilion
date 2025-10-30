# Operations Resources

This directory hosts operational playbooks and deployment extensions for TradingAgents.

## Quick Links

| Resource | Description |
| --- | --- |
| [Main Deployment Guide](../DEPLOYMENT.md) | Consolidated Docker, production, scaling, and maintenance guidance. |
| [Configuration Guide](../CONFIGURATION.md) | Environment variables, vendor routing, alerting options. |
| [API Reference](../API.md) | REST, SSE, WebSocket, and admin endpoints. |
| [Kubernetes Example](./kubernetes-example.md) | Example manifests for Deployments, Services, Ingress, and autoscaling. |

## Common Operational Tasks

```bash
./scripts/deploy.sh up             # Start services
./scripts/deploy.sh down           # Stop services (volumes retained)
./scripts/deploy.sh logs backend   # Tail backend logs
./scripts/deploy.sh migrate        # Apply pending migrations
./scripts/healthcheck.sh           # Run built-in health check
```

## Recommended Practices

- **Security**: Rotate API keys regularly, store secrets outside version control, and enable TLS via nginx or an upstream load balancer.
- **Observability**: Scrape `/monitoring/metrics`, stream logs to your aggregation platform, and enable alerting (`ALERT_EMAIL_*`, `ALERT_WEBHOOK_*`).
- **Resilience**: Use `./scripts/deploy.sh clean` only when you intend to destroy stateful volumes. Schedule database and Redis backups.
- **Scaling**: Adjust Compose profiles or use the Kubernetes manifests as a starting point for managed environments.

## Contributions

Operations evolve quickly. If you automate new hosting targets (cloud platforms, orchestration systems) or refine runbooks, please submit a pull request so the community benefits.
