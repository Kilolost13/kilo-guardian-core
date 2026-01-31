# 📦 Persistent Storage Setup

## ✅ What Was Done

### **1. Added Docker Named Volumes**
All microservices now use persistent Docker volumes instead of `/tmp/`:

- `gateway_data` → Gateway admin tokens
- `ai_brain_data` → AI memories and conversations
- `library_data` → Library of Truth database
- `meds_data` → Medications database
- `reminder_data` → Reminders database
- `financial_data` → Financial transactions
- `habits_data` → Habits tracking

### **2. Updated Database Paths**
Changed from volatile `/tmp/` to persistent `/data/`:
- ✅ Library: `/tmp/library_of_truth.db` → `/data/library_of_truth.db`
- ✅ Meds: `/tmp/meds.db` → `/data/meds.db`

### **3. Auto-Parsing for Library of Truth**
The library now automatically parses PDFs on first startup:
- Checks if database is empty on startup
- If empty, parses all PDFs in `books/` directory
- Extracts text and stores in searchable database
- Only happens once (not on every restart)

### **4. Fixed Library Entry Model**
Added missing fields to properly store PDF content:
- `book` - PDF filename
- `page` - Page number
- `chunk` - Chunk number within page
- `text` - Extracted text content

---

## 🎯 Benefits

### **Data Survives Rebuilds**
- Container rebuilds don't delete your data
- Medications, reminders, memories all persist
- PDF library stays indexed

### **Fast Startup**
- After first parse, library loads instantly
- No re-processing of PDFs each time

### **Automatic Recovery**
- If volume gets deleted, PDFs auto-parse
- System self-heals from data loss

### **Easy Backups**
All data in one place:
```bash
# List volumes
docker volume ls

# Backup a volume
docker run --rm -v library_data:/data -v $(pwd):/backup alpine tar czf /backup/library_backup.tar.gz /data

# Restore a volume
docker run --rm -v library_data:/data -v $(pwd):/backup alpine tar xzf /backup/library_backup.tar.gz -C /
```

---

## 📚 Your PDFs in Library

Currently in `library_of_truth/books/`:
1. **st_31-91b-_us_army_special_forces_medical_handbook.pdf** - Medical reference
2. **fm_5-103_survivability.pdf** - Survival guide
3. **fm-5-34C3(03).pdf** - Engineering/Construction manual
4. **94032625-JACQUES-PEPIN-NEW-COMPLETE-TECHNIQUES-Sampler.pdf** - Cooking techniques
5. **452417530-Master-Basic-DIY-Teach-Yourself.pdf** - DIY manual

**On next startup, all PDFs will be automatically parsed and searchable!**

---

## 🚀 How to Start the System

### **First Time (with auto-parsing)**
```bash
cd "/home/kilo/Desktop/getkrakaen/this is the project file/microservice"

# Set required environment variable
export LIBRARY_ADMIN_KEY="your-secure-key-here"

# Start all services (library will auto-parse PDFs)
docker-compose up -d

# Watch library parsing (first time only)
docker-compose logs -f library_of_truth
```

You'll see:
```
[Library of Truth] Database is empty, parsing PDFs...
[Library of Truth] PDF parsing complete!
```

### **Subsequent Starts (instant)**
```bash
docker-compose up -d
# No parsing - database already exists in volume!
```

---

## 🔍 Verify Data Persistence

### **Check Volumes**
```bash
docker volume ls | grep microservice
```

Should show:
```
microservice_ai_brain_data
microservice_financial_data
microservice_gateway_data
microservice_habits_data
microservice_library_data
microservice_meds_data
microservice_reminder_data
```

### **Check Library Database**
```bash
# After first startup with auto-parsing
docker exec microservice_library_of_truth_1 sqlite3 /data/library_of_truth.db "SELECT COUNT(*) FROM entry;"
```

Should show number of text chunks extracted from PDFs.

### **Test Persistence**
```bash
# Add a medication
curl -X POST http://192.168.68.64:8000/meds/add \
  -H "Content-Type: application/json" \
  -d '{"name":"Aspirin","schedule":"daily","dosage":"100mg","quantity":30,"prescriber":"Dr. Smith","instructions":"Take with food"}'

# Restart services
docker-compose restart meds

# Verify medication still exists
curl http://192.168.68.64:8000/meds/
```

---

## 🗄️ Volume Management

### **Inspect Volume**
```bash
docker volume inspect microservice_library_data
```

### **Remove All Volumes (CAUTION: Deletes all data!)**
```bash
docker-compose down -v
```

### **Remove Single Volume**
```bash
docker volume rm microservice_library_data
# Next startup will auto-parse PDFs again
```

### **Backup Everything**
```bash
#!/bin/bash
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

for vol in gateway_data ai_brain_data library_data meds_data reminder_data financial_data habits_data; do
    docker run --rm \
        -v microservice_${vol}:/data:ro \
        -v "$BACKUP_DIR":/backup \
        alpine tar czf /backup/${vol}.tar.gz /data
done

echo "Backup complete: $BACKUP_DIR"
```

---

## 📝 Adding More PDFs

1. **Copy PDF to library**:
   ```bash
   cp your-book.pdf "/home/kilo/Desktop/getkrakaen/this is the project file/microservice/library_of_truth/books/"
   ```

2. **Option A - Manual parse**:
   ```bash
   curl -X POST http://192.168.68.64:8000/library_of_truth/parse_books \
     -H "X-Admin-Key: your-admin-key"
   ```

3. **Option B - Delete volume and restart** (auto-parses all PDFs):
   ```bash
   docker-compose down
   docker volume rm microservice_library_data
   docker-compose up -d
   ```

---

## 🔧 Troubleshooting

### **Volume Not Created**
```bash
# Manually create volume
docker volume create microservice_library_data

# Restart service
docker-compose up -d library_of_truth
```

### **Permission Errors**
```bash
# Fix volume permissions
docker run --rm -v microservice_library_data:/data alpine chown -R 1000:1000 /data
```

### **Database Corruption**
```bash
# Remove corrupted volume
docker volume rm microservice_library_data

# Restart (auto-parses PDFs)
docker-compose up -d library_of_truth
```

### **Check Volume Location on Host**
```bash
docker volume inspect microservice_library_data | grep Mountpoint
```

---

## ✨ Summary

**Before**: Data in `/tmp/` - lost on every rebuild
**After**: Data in persistent volumes - survives rebuilds

**Before**: Manual PDF parsing via API call
**After**: Automatic parsing on first startup

**Before**: No easy backup strategy
**After**: Simple volume backup with `docker run`

**Your system is now production-ready with persistent storage!**
