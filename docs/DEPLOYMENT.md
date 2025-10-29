# Deployment Guide

This guide covers deploying Coderrr in various environments.

## Table of Contents

1. [Local Development](#local-development)
2. [Production Deployment](#production-deployment)
3. [Docker Deployment](#docker-deployment)
4. [Cloud Deployment](#cloud-deployment)
5. [CI/CD Integration](#cicd-integration)
6. [Monitoring & Logging](#monitoring--logging)
7. [Scaling](#scaling)

---

## Local Development

### Quick Start

```bash
# Clone repository
git clone https://github.com/yourusername/coderrr.git
cd coderrr

# Install dependencies
npm install
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start backend
uvicorn main:app --reload --port 5000

# In another terminal, link CLI
npm link

# Test
coderrr exec "Create a hello world script"
```

### Development Environment Variables

```env
# Required
GITHUB_TOKEN=your_github_token
# OR
MISTRAL_API_KEY=your_mistral_key

# Optional (with defaults)
MISTRAL_ENDPOINT=https://models.inference.ai.azure.com
MISTRAL_MODEL=mistral-large-2411
CODERRR_BACKEND=http://localhost:5000
TIMEOUT_MS=120000
```

---

## Production Deployment

### Prerequisites

- Node.js 16+ (recommended: 18 LTS)
- Python 3.8+ (recommended: 3.11)
- Process manager (PM2, systemd, etc.)
- Reverse proxy (nginx, Apache) - optional
- SSL certificate - recommended

### Step 1: Prepare Environment

```bash
# Create production directory
sudo mkdir -p /opt/coderrr
cd /opt/coderrr

# Clone repository
git clone https://github.com/yourusername/coderrr.git .

# Install dependencies
npm ci --production
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
# Create production .env
cat > .env << EOF
GITHUB_TOKEN=${GITHUB_TOKEN}
MISTRAL_ENDPOINT=https://models.inference.ai.azure.com
MISTRAL_MODEL=mistral-large-2411
CODERRR_BACKEND=http://localhost:5000
TIMEOUT_MS=120000
NODE_ENV=production
EOF

# Secure the file
chmod 600 .env
```

### Step 3: Process Manager (PM2)

```bash
# Install PM2
npm install -g pm2

# Create PM2 ecosystem file
cat > ecosystem.config.js << EOF
module.exports = {
  apps: [
    {
      name: 'coderrr-backend',
      script: 'env/bin/uvicorn',
      args: 'main:app --host 0.0.0.0 --port 5000 --workers 4',
      env: {
        NODE_ENV: 'production'
      },
      error_file: './logs/backend-error.log',
      out_file: './logs/backend-out.log',
      time: true
    }
  ]
};
EOF

# Start backend
pm2 start ecosystem.config.js

# Save PM2 config
pm2 save

# Setup PM2 to start on boot
pm2 startup
```

### Step 4: Systemd Service (Alternative)

```bash
# Create systemd service file
sudo cat > /etc/systemd/system/coderrr-backend.service << EOF
[Unit]
Description=Coderrr Backend Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/coderrr
Environment="PATH=/opt/coderrr/env/bin"
ExecStart=/opt/coderrr/env/bin/uvicorn main:app --host 0.0.0.0 --port 5000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl enable coderrr-backend
sudo systemctl start coderrr-backend

# Check status
sudo systemctl status coderrr-backend
```

### Step 5: Reverse Proxy (Nginx)

```nginx
# /etc/nginx/sites-available/coderrr
server {
    listen 80;
    server_name coderrr.yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name coderrr.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/coderrr.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/coderrr.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Logging
    access_log /var/log/nginx/coderrr-access.log;
    error_log /var/log/nginx/coderrr-error.log;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=coderrr_limit:10m rate=10r/s;
    limit_req zone=coderrr_limit burst=20 nodelay;

    location / {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/coderrr /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Docker Deployment

### Dockerfile

Create `Dockerfile`:

```dockerfile
# Multi-stage build
FROM node:18-alpine AS node-builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --production

FROM python:3.11-slim
WORKDIR /app

# Install Node.js in Python image
COPY --from=node-builder /usr/local/bin/node /usr/local/bin/
COPY --from=node-builder /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm

# Copy application
COPY . .
COPY --from=node-builder /app/node_modules ./node_modules

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN useradd -m -u 1000 coderrr && \
    chown -R coderrr:coderrr /app
USER coderrr

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000').read()"

# Start backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "4"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  coderrr-backend:
    build: .
    container_name: coderrr-backend
    restart: unless-stopped
    ports:
      - "5000:5000"
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - MISTRAL_ENDPOINT=${MISTRAL_ENDPOINT}
      - MISTRAL_MODEL=${MISTRAL_MODEL}
      - CODERRR_BACKEND=http://localhost:5000
      - TIMEOUT_MS=120000
    volumes:
      - ./logs:/app/logs
    networks:
      - coderrr-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

networks:
  coderrr-network:
    driver: bridge
```

### Build and Run

```bash
# Build image
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## Cloud Deployment

### AWS (EC2)

```bash
# Launch EC2 instance (Ubuntu 22.04, t3.medium)

# SSH into instance
ssh -i your-key.pem ubuntu@your-instance-ip

# Install dependencies
sudo apt update
sudo apt install -y nodejs npm python3 python3-pip python3-venv nginx

# Clone and setup (follow Production Deployment steps)

# Configure security group
# - Allow inbound: 22 (SSH), 80 (HTTP), 443 (HTTPS)
# - Allow outbound: All
```

### Google Cloud Platform (Cloud Run)

```bash
# Install gcloud CLI
# https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login
gcloud config set project your-project-id

# Build and push Docker image
gcloud builds submit --tag gcr.io/your-project-id/coderrr

# Deploy to Cloud Run
gcloud run deploy coderrr-backend \
  --image gcr.io/your-project-id/coderrr \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GITHUB_TOKEN=your_token,MISTRAL_ENDPOINT=...,MISTRAL_MODEL=...

# Get service URL
gcloud run services describe coderrr-backend --region us-central1 --format 'value(status.url)'
```

### Azure (Container Instances)

```bash
# Install Azure CLI
# https://docs.microsoft.com/en-us/cli/azure/install-azure-cli

# Login
az login

# Create resource group
az group create --name coderrr-rg --location eastus

# Create container registry
az acr create --resource-group coderrr-rg --name codeerrregistry --sku Basic

# Build and push image
az acr build --registry codeerrregistry --image coderrr:latest .

# Deploy container instance
az container create \
  --resource-group coderrr-rg \
  --name coderrr-backend \
  --image codeerrregistry.azurecr.io/coderrr:latest \
  --dns-name-label coderrr-backend \
  --ports 5000 \
  --environment-variables GITHUB_TOKEN=your_token MISTRAL_ENDPOINT=... MISTRAL_MODEL=...

# Get FQDN
az container show --resource-group coderrr-rg --name coderrr-backend --query ipAddress.fqdn
```

### Heroku

```bash
# Install Heroku CLI
# https://devcenter.heroku.com/articles/heroku-cli

# Login
heroku login

# Create app
heroku create your-app-name

# Add buildpacks
heroku buildpacks:add --index 1 heroku/nodejs
heroku buildpacks:add --index 2 heroku/python

# Set environment variables
heroku config:set GITHUB_TOKEN=your_token
heroku config:set MISTRAL_ENDPOINT=...
heroku config:set MISTRAL_MODEL=...

# Create Procfile
echo "web: uvicorn main:app --host 0.0.0.0 --port \$PORT" > Procfile

# Deploy
git push heroku main

# Open app
heroku open
```

---

## CI/CD Integration

### GitHub Actions

Already provided in `.github/workflows/ci.yml`.

**Deployment workflow**:

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to production
        env:
          SSH_PRIVATE_KEY: ${{ secrets.SSH_PRIVATE_KEY }}
          SERVER_IP: ${{ secrets.SERVER_IP }}
        run: |
          echo "$SSH_PRIVATE_KEY" > key.pem
          chmod 600 key.pem
          ssh -i key.pem -o StrictHostKeyChecking=no ubuntu@$SERVER_IP << 'EOF'
            cd /opt/coderrr
            git pull
            npm ci --production
            source env/bin/activate
            pip install -r requirements.txt
            pm2 restart coderrr-backend
          EOF
```

---

## Monitoring & Logging

### Application Logs

```bash
# PM2 logs
pm2 logs coderrr-backend

# Systemd logs
sudo journalctl -u coderrr-backend -f

# Docker logs
docker-compose logs -f
```

### Health Monitoring

```bash
# Simple health check script
cat > health-check.sh << 'EOF'
#!/bin/bash
BACKEND_URL="http://localhost:5000"

if curl -f -s $BACKEND_URL > /dev/null; then
    echo "✅ Backend is healthy"
    exit 0
else
    echo "❌ Backend is down"
    exit 1
fi
EOF

chmod +x health-check.sh

# Add to cron (check every 5 minutes)
crontab -e
# Add: */5 * * * * /opt/coderrr/health-check.sh
```

### Prometheus Monitoring

Add to `main.py`:

```python
from prometheus_fastapi_instrumentator import Instrumentator

# After app creation
Instrumentator().instrument(app).expose(app)
```

---

## Scaling

### Horizontal Scaling (Multiple Instances)

**Load Balancer Configuration** (Nginx):

```nginx
upstream coderrr_backends {
    least_conn;
    server backend1.local:5000 weight=1;
    server backend2.local:5000 weight=1;
    server backend3.local:5000 weight=1;
}

server {
    listen 443 ssl http2;
    server_name coderrr.yourdomain.com;
    
    location / {
        proxy_pass http://coderrr_backends;
        # ... proxy settings ...
    }
}
```

### Vertical Scaling (Increase Resources)

```bash
# Increase workers in uvicorn
uvicorn main:app --workers 8  # Match CPU cores

# Increase memory limit (Docker)
docker run -m 4g coderrr:latest

# Increase EC2 instance size
# t3.medium → t3.large → t3.xlarge
```

---

## Security Checklist

- [ ] Use HTTPS (SSL/TLS)
- [ ] Set strong firewall rules
- [ ] Use environment variables for secrets
- [ ] Enable rate limiting
- [ ] Keep dependencies updated
- [ ] Use non-root user in Docker
- [ ] Enable application logging
- [ ] Regular security audits (`npm audit`, `safety check`)
- [ ] Use secrets management (AWS Secrets Manager, Azure Key Vault)
- [ ] Implement request validation
- [ ] Use CORS properly
- [ ] Monitor for anomalies

---

## Backup & Recovery

### Configuration Backup

```bash
# Backup .env and configs
tar -czf coderrr-config-$(date +%Y%m%d).tar.gz .env ecosystem.config.js

# Upload to S3
aws s3 cp coderrr-config-*.tar.gz s3://your-backup-bucket/
```

### Disaster Recovery

```bash
# 1. Stop services
pm2 stop all

# 2. Backup current state
tar -czf coderrr-backup-$(date +%Y%m%d).tar.gz /opt/coderrr

# 3. Restore from backup
tar -xzf coderrr-backup-YYYYMMDD.tar.gz -C /opt/

# 4. Restart services
pm2 restart all
```

---

For more details, see [ARCHITECTURE.md](ARCHITECTURE.md) and [FAQ.md](FAQ.md).
