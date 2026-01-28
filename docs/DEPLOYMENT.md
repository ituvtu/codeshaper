# Deployment Guide

This document describes how to deploy the CodeShaper LLM API using Docker and other tools.

## Table of Contents
1. [Local Development](#local-development)
2. [Docker for Development](#docker-for-development)
3. [Production Deployment](#production-deployment)
4. [CI/CD Pipeline](#cicd-pipeline)
5. [Secrets Management](#secrets-management)
6. [Monitoring and Logging](#monitoring-and-logging)

---

## Local Development

### Requirements
- Python 3.11+
- Poetry
- Git

### Installation
```bash
# Clone the repository
git clone https://github.com/ituvtu/codeshaper.git
cd codeshaper

# Install dependencies
poetry install

# Copy .env file
cp .env.example .env
# Edit .env and add your Groq API key
```

### Running
```bash
# Activate venv and run the server
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# On another terminal for testing
poetry run pytest tests/ -v
```

API will be available at `http://localhost:8000`
Documentation: `http://localhost:8000/docs`

---

## Docker for Development

### Requirements
- Docker Desktop (or Docker + Docker Compose)
- 4GB+ RAM (recommended)

### Development with hot reload

```bash
# Copy .env
cp .env.example .env

# Run compose with hot reload
docker-compose -f deployment/docker-compose.dev.yml up

# On another terminal for testing
docker-compose -f deployment/docker-compose.dev.yml exec api poetry run pytest tests/
```

**Features:**
- Hot reload on code changes in `app/`
- Redis starts automatically
- Port routing: 8000
- Volumes for quick development

### Stop
```bash
docker-compose -f deployment/docker-compose.dev.yml down
```

---

## Production Deployment

### Prerequisites
- Groq API key
- Docker and Docker Compose on server
- SSL certificate (recommended)
- Minimum 1GB free memory

### Server Preparation

```bash
# 1. Update system
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 3. Download repository
git clone https://github.com/ituvtu/codeshaper.git /opt/codeshaper
cd /opt/codeshaper

# 4. Create .env for production
cat > .env << EOF
API_KEY=your_groq_api_key_here
MODEL=llama-3.1-8b-instant
REDIS_URL=redis://redis:6379/0
PORT=8000
LOG_LEVEL=info
EOF

# 5. Set permissions
sudo chown -R $(id -u):$(id -g) /opt/codeshaper
```

### Running Production Service

```bash
# Without SSL
docker-compose -f deployment/docker-compose.prod.yml up -d

# With SSL (if you have certificates)
# 1. Place cert.pem and key.pem in current directory
# 2. Uncomment SSL section in nginx.conf
# 3. Run:
docker-compose -f deployment/docker-compose.prod.yml up -d
```

### Checking Status

```bash
# Check container status
docker-compose -f deployment/docker-compose.prod.yml ps

# Check API logs
docker-compose -f deployment/docker-compose.prod.yml logs api

# Check Nginx logs
docker-compose -f deployment/docker-compose.prod.yml logs nginx

# Check health endpoint
curl http://localhost/health
```

### Scaling

```bash
# Increase number of API instances (if using a load balancer)
docker-compose -f deployment/docker-compose.prod.yml up -d --scale api=3

# Or manually edit docker-compose.yml and change replicas
```

---

## CI/CD Pipeline

### GitHub Actions Setup

1. **Add Secrets on GitHub:**
   ```
   Settings → Secrets and variables → Actions
   ```
   Required:
   - `DOCKER_USERNAME` - Docker Hub username
   - `DOCKER_PASSWORD` - Docker Hub password
   - `SERVER_IP` - IP of your production server
   - `DEPLOY_KEY` - SSH private key

2. **Workflow runs on:**
   - Push to `main` or `develop`
   - Pull requests
   - Tag push (v1.0.0 format for release)

3. **Pipeline Steps:**
   - ✅ Testing (Python 3.11, 3.12, 3.13)
   - ✅ Linting (Pylint, Mypy, Black)
   - ✅ Coverage analysis
   - 🐳 Docker build and push (on tag)
   - 🚀 Production deploy (manually triggered)

---

## Secrets Management

### Local Secrets

```bash
# Never commit .env with real keys!
cp .env.example .env
echo ".env" >> .gitignore
```

### Production Secrets

**Option 1: Docker secrets (for Swarm)**
```bash
echo "gsk_your_key" | docker secret create groq_api_key -
docker-compose.yml:
  environment:
    API_KEY_FILE: /run/secrets/groq_api_key
```

**Option 2: Environment file**
```bash
# On server
echo "API_KEY=gsk_..." > /opt/codeshaper/.env.production
chmod 600 /opt/codeshaper/.env.production

# docker-compose.yml
env_file:
  - .env.production
```

**Option 3: AWS Secrets Manager / HashiCorp Vault**
```bash
# Install client and retrieve secrets before running
aws secretsmanager get-secret-value --secret-id codeshaper-secrets
```

### HTTPS/SSL Certificates

**Let's Encrypt with Certbot:**
```bash
sudo certbot certonly --standalone -d api.yourdomain.com
sudo cp /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem ./cert.pem
sudo cp /etc/letsencrypt/live/api.yourdomain.com/privkey.pem ./key.pem
```

---

## Monitoring and Logging

### Viewing Logs

```bash
# API logs
docker-compose logs -f api

# Nginx logs
docker-compose logs -f nginx

# Redis logs
docker-compose logs -f redis

# All together
docker-compose logs -f
```

### Metrics and Monitoring

Add to production docker-compose.yml:

```yaml
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
```

### Health Checks

Endpoint `/health` returns:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0"
}
```

Check regularly:
```bash
# From server
while true; do 
  curl -s http://localhost/health | jq .
  sleep 60
done
```

---

## Automatic Updates

### Via GitHub Actions

1. Make changes in code
2. Push to develop
3. Create Pull Request
4. Merge to main after approval
5. Create new release tag (v1.0.1)
6. CI/CD automatically:
   - Runs tests
   - Builds Docker image
   - Pushes to registry
   - (Optional) deploys to production

### Manual Update

```bash
cd /opt/codeshaper
git pull origin main
docker-compose -f deployment/docker-compose.prod.yml down
docker-compose -f deployment/docker-compose.prod.yml pull
docker-compose -f deployment/docker-compose.prod.yml up -d
```

---

## Troubleshooting

### Issue: API Not Responding

```bash
# 1. Check container
docker-compose -f deployment/docker-compose.prod.yml ps

# 2. Check logs
docker-compose -f deployment/docker-compose.prod.yml logs api

# 3. Check ports
netstat -tulpn | grep 8000

# 4. Restart
docker-compose -f deployment/docker-compose.prod.yml restart api
```

### Issue: Out of Memory

```bash
# Check usage
docker stats

# Increase in docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          memory: 4G
```

### Issue: Nginx 502 Bad Gateway

```bash
# Check that API container is running
docker-compose -f deployment/docker-compose.prod.yml logs api

# Check nginx config
docker-compose -f deployment/docker-compose.prod.yml exec nginx nginx -t

# Restart nginx
docker-compose -f deployment/docker-compose.prod.yml restart nginx
```

---

## Backups and Recovery

```bash
# Backup Redis data
docker cp codeshaper-redis-1:/data/dump.rdb ./backup/redis-$(date +%Y%m%d).rdb

# Restore
docker cp ./backup/redis-20240115.rdb codeshaper-redis-1:/data/dump.rdb
docker-compose -f deployment/docker-compose.prod.yml restart redis
```

---

## Security

### Recommendations

- ✅ Always use HTTPS in production
- ✅ Regularly update dependencies: `poetry update`
- ✅ Use non-root user (already configured)
- ✅ Restrict API access via firewall
- ✅ Rotate secrets regularly
- ✅ Monitor logs for anomalies

### Firewall Rules

```bash
# Allow only HTTPS and SSH
sudo ufw default deny incoming
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## Next Steps

1. [Install SSL certificate](#httpssssl-certificates)
2. [Set up monitoring](#metrics-and-monitoring)
3. [Add authentication](#optional-authentication)
4. [Configure CI/CD](#cicd-pipeline)

Questions? Open an issue on GitHub!

