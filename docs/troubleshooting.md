# AI Memory Assistant - Troubleshooting Guide

Generated on: 2025-12-24 08:01:57

## Quick Diagnosis

### System Health Check
```bash
# Check if services are running
curl http://localhost:8000/health

# Check database connection
python3 -c "from ai_brain.db import get_session; sess = get_session(); print('DB OK' if sess else 'DB FAIL')"

# Check frontend build
cd front\ end/kilo-react-frontend && npm run build
```

## Common Issues & Solutions

### 🔴 Application Won't Start

#### Backend Won't Start
**Symptoms:**
- "Module not found" errors
- Import errors
- Port already in use

**Solutions:**
```bash
# Check Python version
python3 --version  # Should be 3.8+

# Verify virtual environment
which python3  # Should point to venv/bin/python3

# Install missing dependencies
pip install -r requirements.txt

# Check for port conflicts
lsof -i :8000  # Kill process if needed

# Run with debug logging
DEBUG=1 python3 ai_brain/main.py
```

#### Frontend Won't Start
**Symptoms:**
- Build failures
- Module resolution errors
- Port conflicts

**Solutions:**
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Check Node.js version
node --version  # Should be 16+

# Free up port 3000
lsof -ti:3000 | xargs kill -9

# Start with different port
PORT=3001 npm start
```

### 🟡 Database Connection Issues

#### Connection Refused
**Symptoms:**
- "Connection refused" errors
- Database operations fail

**Solutions:**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Start PostgreSQL
sudo systemctl start postgresql

# Check connection string
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Reset database
alembic downgrade base
alembic upgrade head
```

#### Migration Errors
**Symptoms:**
- Alembic migration failures
- Schema mismatch errors

**Solutions:**
```bash
# Check migration status
alembic current

# View pending migrations
alembic history

# Reset and reapply migrations
alembic downgrade base
alembic upgrade head

# Manual migration fix
alembic revision --autogenerate -m "fix migration"
```

### 🟠 Performance Issues

#### Slow Response Times
**Symptoms:**
- API calls take >5 seconds
- Frontend feels sluggish

**Solutions:**
```bash
# Check system resources
top  # CPU/memory usage
df -h  # Disk space

# Enable query logging
export SQLALCHEMY_ECHO=1

# Check database indexes
psql -c "SELECT * FROM pg_indexes WHERE tablename = 'memory';"

# Restart services
docker-compose restart

# Clear caches
redis-cli FLUSHALL  # If using Redis
```

#### Memory Leaks
**Symptoms:**
- Increasing memory usage over time
- Out of memory errors

**Solutions:**
```bash
# Monitor memory usage
python3 -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.1f} MB')
"

# Check for connection leaks
# Add connection pooling limits in db.py

# Restart application
docker-compose restart ai-brain
```

### 🟢 Data Issues

#### Missing Data
**Symptoms:**
- Memories/conversations not showing
- Data appears corrupted

**Solutions:**
```bash
# Check database contents
psql -c "SELECT COUNT(*) FROM memory;"
psql -c "SELECT COUNT(*) FROM conversation;"

# Verify data integrity
python3 -c "
from ai_brain.db import get_session
from ai_brain.models import Memory
from sqlalchemy import select
sess = get_session()
memories = sess.exec(select(Memory)).all()
print(f'Found {len(memories)} memories')
"

# Restore from backup
psql ai_memory_db < backup_file.sql
```

#### Search Not Working
**Symptoms:**
- Memory search returns no results
- Full-text search failures

**Solutions:**
```bash
# Rebuild search indexes
psql -c "REINDEX INDEX memory_content_idx;"

# Check search configuration
psql -c "SELECT * FROM pg_ts_config;"

# Test search manually
psql -c "SELECT * FROM memory WHERE content @@ plainto_tsquery('english', 'test query');"
```

### 🔵 Frontend Issues

#### Component Not Rendering
**Symptoms:**
- Blank pages or missing components
- Console errors in browser

**Solutions:**
```bash
# Check browser console for errors
# Open DevTools (F12) → Console tab

# Verify API endpoints
curl http://localhost:8000/health

# Check CORS headers
curl -I http://localhost:8000/api/memory

# Rebuild frontend
cd front\ end/kilo-react-frontend
npm run build
npm start
```

#### Voice Input Not Working
**Symptoms:**
- Microphone icon doesn't respond
- Voice recognition fails

**Solutions:**
```bash
# Check browser permissions
# Chrome: Settings → Privacy → Microphone

# Test microphone access
# Open browser console and run:
navigator.mediaDevices.getUserMedia({audio: true})

# Check HTTPS requirement
# Voice input requires HTTPS in production

# Test speech recognition API
# Open browser console and run:
new webkitSpeechRecognition()
```

### 🟣 Network Issues

#### CORS Errors
**Symptoms:**
- "CORS policy" errors in browser console
- API calls blocked

**Solutions:**
```python
# Check CORS configuration in main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### Connection Timeouts
**Symptoms:**
- Requests timeout after 30 seconds
- Intermittent connection failures

**Solutions:**
```bash
# Increase timeout settings
# In frontend API client
const api = axios.create({
    timeout: 60000,  // 60 seconds
});

# Check network connectivity
ping localhost
curl http://localhost:8000/health

# Check firewall settings
sudo ufw status
```

## Advanced Diagnostics

### Log Analysis
```bash
# View application logs
docker-compose logs ai-brain

# Search for errors
docker-compose logs ai-brain | grep ERROR

# Follow logs in real-time
docker-compose logs -f ai-brain
```

### Database Analysis
```bash
# Check table sizes
psql -c "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size FROM pg_tables ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"

# Find slow queries
psql -c "SELECT query, calls, total_time, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# Check connection count
psql -c "SELECT count(*) FROM pg_stat_activity;"
```

### Performance Profiling
```bash
# Profile Python code
python3 -m cProfile -s time ai_brain/main.py

# Memory profiling
python3 -c "
import tracemalloc
tracemalloc.start()
# Run your code
current, peak = tracemalloc.get_traced_memory()
print(f'Current memory usage: {current / 1024 / 1024:.1f} MB')
print(f'Peak memory usage: {peak / 1024 / 1024:.1f} MB')
"
```

## Emergency Recovery

### Complete System Reset
```bash
# Stop all services
docker-compose down

# Backup current data
pg_dump ai_memory_db > emergency_backup.sql

# Reset database
dropdb ai_memory_db
createdb ai_memory_db

# Reapply migrations
alembic upgrade head

# Restart services
docker-compose up -d
```

### Data Recovery
```bash
# Restore from backup
psql ai_memory_db < emergency_backup.sql

# Verify data integrity
python3 -c "
from ai_brain.db import get_session
from ai_brain.models import Memory
sess = get_session()
count = sess.query(Memory).count()
print(f'Recovered {count} memories')
"
```

## Getting Help

### Debug Information
When reporting issues, include:
- System information (`uname -a`)
- Python/Node.js versions
- Database version
- Full error messages and stack traces
- Steps to reproduce the issue
- Recent changes to the codebase

### Support Checklist
- [ ] Run the test suite: `python3 test_suite.py`
- [ ] Check system health: `curl http://localhost:8000/health`
- [ ] Verify database connection
- [ ] Check logs for errors
- [ ] Test with minimal configuration

---

*Remember: Most issues can be resolved by checking logs, verifying configurations, and running the test suite. Stay calm and debug systematically!*
