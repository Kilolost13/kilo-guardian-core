# 🚀 KILO AI MEMORY ASSISTANT - QUICK START GUIDE

## Get Running in 3 Minutes

### **Option 1: Full System (Backend + Frontend)**

```bash
# Navigate to project
cd "/home/kilo/Desktop/getkrakaen/this is the project file/microservice"

# Start all backend services
docker-compose up -d

# Wait 30 seconds for services to start, then start frontend
cd "front end /kilo-react-frontend"
npm start
```

**Access**: http://localhost:3000

---

### **Option 2: Frontend Only (Development)**

```bash
cd "/home/kilo/Desktop/getkrakaen/this is the project file/microservice/front end /kilo-react-frontend"
npm start
```

**Note**: Backend must be running separately for full functionality.

---

### **Option 3: Production Build**

```bash
cd "/home/kilo/Desktop/getkrakaen/this is the project file/microservice"

# Build and start everything
docker-compose up -d --build
```

**Access**: http://localhost:3000

---

## First-Time Setup

### **1. Install Dependencies (First Time Only)**

```bash
cd "/home/kilo/Desktop/getkrakaen/this is the project file/microservice/front end /kilo-react-frontend"
npm install --legacy-peer-deps
```

### **2. Create Admin Token**

```bash
# After backend is running
curl -X POST http://localhost:8000/admin/tokens

# Save the token returned!
```

### **3. Test Chat**

```bash
# Store a memory
curl -X POST http://localhost:9004/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "/remember I like pizza", "user": "test"}'

# Recall memories
curl -X POST http://localhost:9004/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "/recall food", "user": "test"}'
```

---

## Available Pages

Once running, you can access:

- **Dashboard**: http://localhost:3000 (AI chat + navigation)
- **Medications**: http://localhost:3000/meds
- **Reminders**: http://localhost:3000/reminders
- **Finance**: http://localhost:3000/finance
- **Habits**: http://localhost:3000/habits
- **Admin**: http://localhost:3000/admin

---

## Verify Services Are Running

```bash
cd "/home/kilo/Desktop/getkrakaen/this is the project file/microservice"
docker-compose ps
```

**Expected**:
```
NAME                  SERVICE       STATUS
microservice-gateway     gateway       Up
microservice-ai_brain    ai_brain      Up
microservice-meds        meds          Up
microservice-reminder    reminder      Up
microservice-financial   financial     Up
microservice-habits      habits        Up
microservice-library     library       Up
microservice-cam         cam           Up
microservice-frontend    frontend      Up
```

---

## Common Commands

```bash
# Stop everything
docker-compose down

# Restart a service
docker-compose restart ai_brain

# View logs
docker-compose logs -f ai_brain

# Rebuild and start
docker-compose up -d --build

# Frontend dev mode
cd "front end /kilo-react-frontend" && npm start

# Frontend production build
cd "front end /kilo-react-frontend" && npm run build
```

---

## Troubleshooting

### **Frontend won't start**
```bash
cd "front end /kilo-react-frontend"
npm install --legacy-peer-deps
npm start
```

### **Backend services won't start**
```bash
docker-compose down
docker-compose up -d --build
docker-compose logs
```

### **Chat not working**
1. Check backend is running: `docker-compose ps`
2. Check AI Brain logs: `docker-compose logs ai_brain`
3. Verify API URL in browser console (F12)

### **Can't connect to API**
1. Check `.env` has correct `REACT_APP_API_BASE_URL`
2. Verify gateway is running on port 8000
3. Check browser console for CORS errors

---

## What to Test First

1. ✅ **Dashboard** - Open http://localhost:3000
2. ✅ **Chat** - Type "hello" and press Enter
3. ✅ **Store Memory** - Type `/remember I like coding`
4. ✅ **Recall Memory** - Type `/recall coding`
5. ✅ **Navigate** - Click "MEDS" tile
6. ✅ **Check Status** - Go to Admin panel

---

## Documentation

- **Complete Summary**: [COMPLETE_PROJECT_SUMMARY.md](COMPLETE_PROJECT_SUMMARY.md)
- **Air-Gapped Deployment**: [microservice/README_AIRGAP.md](microservice/README_AIRGAP.md)
- **Frontend Details**: [microservice/frontend/kilo-react-frontend/IMPLEMENTATION_COMPLETE.md](microservice/frontend/kilo-react-frontend/IMPLEMENTATION_COMPLETE.md)
- **Backend Summary**: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- **UI Wireframes**: [TABLET_UI_WIREFRAMES.md](TABLET_UI_WIREFRAMES.md)

---

## Need Help?

1. Check logs: `docker-compose logs -f`
2. Verify all services: `docker-compose ps`
3. Check browser console (F12)
4. Review documentation files above

---

**🎉 You're ready to use your AI Memory Assistant!**
