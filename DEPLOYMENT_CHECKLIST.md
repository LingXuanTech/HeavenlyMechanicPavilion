# TradingAgents Deployment Checklist

Use this checklist to ensure a smooth deployment of TradingAgents.

## Pre-Deployment Checklist

### System Requirements
- [ ] Docker Engine 20.10+ installed
- [ ] Docker Compose V2 installed
- [ ] Minimum 4GB RAM available (8GB+ recommended)
- [ ] At least 20GB free disk space
- [ ] Network connectivity for pulling images and accessing APIs

### API Keys and Credentials
- [ ] OpenAI API key obtained
- [ ] Alpha Vantage API key obtained
- [ ] Generated secure PostgreSQL password
- [ ] Generated secure Redis password
- [ ] (Optional) Anthropic API key if using Claude
- [ ] (Optional) Google API key if using Gemini

### Configuration Files
- [ ] Copied `.env.docker` to `.env`
- [ ] Updated `OPENAI_API_KEY` in `.env`
- [ ] Updated `ALPHA_VANTAGE_API_KEY` in `.env`
- [ ] Updated `POSTGRES_PASSWORD` in `.env`
- [ ] Updated `REDIS_PASSWORD` in `.env`
- [ ] Reviewed and adjusted LLM model settings
- [ ] Configured service ports if defaults conflict

## Development Deployment

### Initial Setup
- [ ] Environment file configured: `cp .env.docker .env`
- [ ] Scripts are executable: `chmod +x scripts/*.sh`
- [ ] Docker daemon is running: `docker ps`

### Start Services
- [ ] Started core services: `./scripts/deploy.sh up`
- [ ] Waited for services to initialize (~30-60 seconds)
- [ ] Checked service status: `./scripts/deploy.sh ps`
- [ ] Verified logs: `./scripts/deploy.sh logs`

### Health Verification
- [ ] Backend health check passes: `curl http://localhost:8000/health`
- [ ] Database connection successful
- [ ] Redis connection successful
- [ ] Ran comprehensive health check: `./scripts/healthcheck.sh`

### Optional Services
- [ ] Frontend deployed (if needed): `PROFILE=frontend ./scripts/deploy.sh up`
- [ ] Workers deployed (if needed): `PROFILE=workers ./scripts/deploy.sh up`
- [ ] Nginx deployed (if needed): `PROFILE=nginx ./scripts/deploy.sh up`

## Production Deployment

### Security Hardening
- [ ] Changed all default passwords
- [ ] Used strong passwords (32+ characters)
- [ ] Disabled debug mode: `DEBUG=false`
- [ ] Disabled database echo: `DATABASE_ECHO=false`
- [ ] Reviewed `.gitignore` to prevent secret leaks
- [ ] Secrets not committed to version control

### SSL/TLS Configuration
- [ ] SSL certificates obtained (Let's Encrypt or purchased)
- [ ] Certificates placed in `nginx/ssl/`
- [ ] Updated `nginx/nginx.conf` with certificate paths
- [ ] Enabled HTTPS redirect in nginx config
- [ ] Tested SSL configuration

### Database Setup
- [ ] PostgreSQL persistence configured
- [ ] Database backups scheduled
- [ ] Migration tested: `./scripts/deploy.sh migrate`
- [ ] Database connection string uses PostgreSQL (not SQLite)

### Resource Configuration
- [ ] Resource limits set in `docker-compose.prod.yml`
- [ ] Memory limits appropriate for workload
- [ ] CPU limits configured
- [ ] Disk space monitoring enabled

### Deployment
- [ ] Built production images: `./scripts/deploy.sh build`
- [ ] Started with production config:
  ```bash
  docker compose -f docker-compose.yml -f docker-compose.prod.yml \
    --profile frontend --profile workers --profile nginx up -d
  ```
- [ ] Verified all services started
- [ ] Checked logs for errors
- [ ] Ran health checks

### Monitoring Setup
- [ ] Metrics enabled: `METRICS_ENABLED=true`
- [ ] Prometheus endpoint accessible: `/metrics`
- [ ] Log aggregation configured
- [ ] Alerting configured (if using)
- [ ] Health check monitoring setup

### Testing
- [ ] API endpoints respond correctly
- [ ] WebSocket connections work
- [ ] SSE streaming functional
- [ ] Frontend loads (if deployed)
- [ ] Workers processing tasks (if deployed)
- [ ] Database queries perform well
- [ ] Redis caching working

## Scaling Checklist

### Horizontal Scaling
- [ ] Backend scaled to desired replicas: `docker compose up -d --scale backend=3`
- [ ] Workers scaled to desired replicas: `docker compose --profile workers up -d --scale worker=5`
- [ ] Load balancer (nginx) configured
- [ ] Health checks passing for all replicas

### Vertical Scaling
- [ ] Resource limits adjusted in `docker-compose.prod.yml`
- [ ] Services restarted with new limits
- [ ] Performance monitored after changes

## Monitoring and Maintenance

### Regular Checks
- [ ] Daily health check: `./scripts/healthcheck.sh`
- [ ] Log review: `./scripts/deploy.sh logs`
- [ ] Resource usage monitoring: `docker stats`
- [ ] Disk space check: `df -h`
- [ ] Database size monitoring

### Backup Procedures
- [ ] Database backup script tested
- [ ] Backup schedule configured
- [ ] Backup restoration tested
- [ ] Backup storage secured
- [ ] Backup retention policy defined

### Update Procedures
- [ ] Update process documented
- [ ] Rollback procedure defined
- [ ] Migration strategy planned
- [ ] Downtime window scheduled (if needed)

## Post-Deployment Verification

### Functional Testing
- [ ] Created test trading session via API
- [ ] Verified session completes successfully
- [ ] Checked result storage
- [ ] Tested error handling
- [ ] Verified rate limiting works

### Performance Testing
- [ ] Response times acceptable
- [ ] Concurrent request handling tested
- [ ] Database query performance checked
- [ ] Memory usage stable
- [ ] No memory leaks detected

### Security Verification
- [ ] Only necessary ports exposed
- [ ] SSL/TLS working correctly
- [ ] Rate limiting active
- [ ] Authentication working (if implemented)
- [ ] Secrets properly secured

## Troubleshooting Resources

### Common Issues Reference
- [ ] Reviewed troubleshooting section in `DEPLOYMENT.md`
- [ ] Documented custom issues encountered
- [ ] Created runbook for common problems

### Support Contacts
- [ ] Discord community link saved
- [ ] GitHub issues page bookmarked
- [ ] Emergency contacts documented

## Documentation

### Team Documentation
- [ ] Deployment process documented
- [ ] Configuration explained
- [ ] Scaling procedures documented
- [ ] Backup/restore procedures documented
- [ ] Troubleshooting guide created

### Operational Runbook
- [ ] Start/stop procedures
- [ ] Health check procedures
- [ ] Incident response procedures
- [ ] Escalation path defined

## Compliance and Legal

### Data and Privacy
- [ ] Data storage locations documented
- [ ] Privacy policy reviewed
- [ ] Compliance requirements met
- [ ] Data retention policy defined

### Terms and Disclaimers
- [ ] TradingAgents disclaimer acknowledged
- [ ] API terms of service reviewed (OpenAI, Alpha Vantage)
- [ ] Usage limits understood
- [ ] Cost implications calculated

## Final Sign-off

### Pre-Production
- [ ] All checklist items completed
- [ ] Stakeholders notified
- [ ] Maintenance window scheduled
- [ ] Rollback plan ready

### Production Go-Live
- [ ] Services deployed
- [ ] Health checks passing
- [ ] Monitoring active
- [ ] Team notified
- [ ] Documentation updated

### Post-Go-Live
- [ ] System stable for 24 hours
- [ ] No critical errors in logs
- [ ] Performance metrics acceptable
- [ ] Backup completed successfully
- [ ] Post-deployment review scheduled

## Notes

Use this section to document deployment-specific notes:

```
Date: _____________
Deployed by: _____________
Environment: _____________
Version/Commit: _____________

Notes:
_______________________________________
_______________________________________
_______________________________________
```

## Quick Reference

### Essential Commands
```bash
# Start services
./scripts/deploy.sh up

# Health check
./scripts/healthcheck.sh

# View logs
./scripts/deploy.sh logs -f

# Run migrations
./scripts/deploy.sh migrate

# Stop services
./scripts/deploy.sh down

# Backup database
docker compose exec postgres pg_dump -U tradingagents tradingagents > backup.sql
```

### Emergency Contacts
- Discord: https://discord.com/invite/hk9PGKShPK
- GitHub: https://github.com/TauricResearch/TradingAgents/issues
- Docs: See DEPLOYMENT.md

---

**Remember**: This is a research framework. See [disclaimer](https://tauric.ai/disclaimer/) for important information about trading and financial use.
