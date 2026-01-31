# AI Memory Assistant - Deployment Guide

Generated on: 2025-12-24 08:01:57

## Overview

This guide covers deploying the AI Memory Assistant in air-gapped environments.

## Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Docker (optional)
- Kubernetes (optional, for production)

## Local Development Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd ai-memory-assistant
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate   # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Database
```bash
# Install PostgreSQL locally or use Docker
docker run --name postgres -e POSTGRES_PASSWORD=password -d -p 5432:5432 postgres:13

# Create database
createdb ai_memory_db
```

### 5. Configure Environment
```bash
# Copy and edit environment file
cp .env.example .env
# Edit .env with your database URL and secrets
```

### 6. Run Database Migrations
```bash
alembic upgrade head
```

### 7. Start the Application
```bash
# Backend
python3 ai_brain/main.py

# Frontend (in another terminal)
cd front\ end/kilo-react-frontend
npm install
npm start
```

## Docker Deployment

### Build Images
```bash
# Build backend
docker build -t ai-memory-backend ./ai_brain

# Build frontend
docker build -t ai-memory-frontend ./front\ end/kilo-react-frontend
```

### Run with Docker Compose
```bash
docker-compose up -d
```

## Production Deployment

### 1. Environment Setup
- Set `ENVIRONMENT=production` in environment variables
- Configure production database
- Set secure JWT secrets
- Enable HTTPS

### 2. Security Configuration
```bash
# Set secure environment variables
export JWT_SECRET_KEY="your-secure-random-key"
export ADMIN_TOKEN="secure-admin-token"
export DATABASE_URL="postgresql://user:password@host:5432/db"
```

### 3. Process Management
```bash
# Using systemd
sudo cp deploy/ai-memory.service /etc/systemd/system/
sudo systemctl enable ai-memory
sudo systemctl start ai-memory

# Using PM2
pm2 start ai_brain/main.py --name "ai-memory"
pm2 save
pm2 startup
```

### 4. Reverse Proxy Setup (nginx)
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Monitoring

### Health Checks
- Health endpoint: `GET /health`
- Metrics endpoint: `GET /metrics` (if Prometheus enabled)

### Logs
- Application logs: Check stdout/stderr or configured log files
- Database logs: Check PostgreSQL logs
- System logs: `journalctl -u ai-memory` (systemd)

## Backup and Recovery

### Database Backup
```bash
# Create backup
pg_dump ai_memory_db > backup_$(date +%Y%m%d).sql

# Restore backup
psql ai_memory_db < backup_20231224.sql
```

### Configuration Backup
```bash
# Backup environment and config files
tar -czf config_backup.tar.gz .env docker-compose.yml
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check DATABASE_URL in environment
   - Verify PostgreSQL is running
   - Check network connectivity

2. **Application Won't Start**
   - Check Python version (3.8+ required)
   - Verify all dependencies installed
   - Check for port conflicts (default: 8000)

3. **Frontend Not Loading**
   - Verify frontend build completed
   - Check CORS settings
   - Verify API endpoints accessible

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python3 ai_brain/main.py
```

## Performance Tuning

### Database Optimization
- Ensure proper indexing on frequently queried columns
- Monitor slow queries with PostgreSQL logs
- Consider connection pooling for high traffic

### Application Optimization
- Enable Redis caching for frequently accessed data
- Configure appropriate worker processes
- Monitor memory usage and adjust as needed

