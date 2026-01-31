# 🧪 Testing on Older Hardware (2012 System with 32GB RAM)

Your 2012 system is **perfect for testing**! Here's how to run Kilo AI in lightweight mode.

---

## ✅ What Works Without Heavy LLM

- ✅ **All ML predictions** (habit completion probability, optimal timing)
- ✅ **Pattern detection** (weekly patterns, streaks, anomalies)
- ✅ **Finance tracking** with receipt OCR
- ✅ **Medication tracking** with prescription OCR
- ✅ **Habits tracking** with progress bars
- ✅ **Semantic memory search** (sentence-transformers embeddings)
- ✅ **Dashboard insights** widget
- ✅ **Admin testing page**

## ❌ What's Disabled for Testing

- ❌ **Ollama LLM** (Llama 3.1 8B) - saves ~2GB RAM, reduces CPU load
- ❌ **Voice features** (Whisper/Piper) - not implemented yet anyway
- ❌ **AI Brain chat** - will return placeholder responses

---

## 🚀 Quick Start

### **1. Navigate to microservice directory**

```bash
cd "/home/kilo/Desktop/getkrakaen/this is the project file/microservice"
```

### **2. Start in lightweight mode**

```bash
# Use the test configuration (skips Ollama)
docker-compose -f docker-compose.test.yml up --build
```

This will:
- Build all 9 services
- Skip the heavy Ollama LLM
- Use ~4GB RAM total (you have 32GB, so plenty of headroom!)
- Take about 5-10 minutes to build on 2012 hardware

### **3. Access the frontend**

Open your browser to:
```
http://localhost:3000
```

---

## 📊 Expected Build Time on Your Hardware

| Task | Time (2012 System) | RAM Used |
|------|-------------------|----------|
| Building backend images | 5-8 minutes | 2-3GB |
| Building frontend (React) | 3-5 minutes | 1-2GB |
| Starting services | 30-60 seconds | 4GB total |
| **Total** | **8-15 minutes** | **~4-6GB** |

---

## 🎯 What to Test

### **A. Habits Module with ML Predictions**

1. Go to **Habits** page
2. Click **"+ Add Habit"**
3. Create a habit:
   - Name: "Morning workout"
   - Frequency: Daily
   - Target: 1 per day
4. Mark it as complete a few times
5. Check for **ML prediction card** showing:
   - Completion probability (e.g., 85%)
   - Confidence score
   - Recommendation

### **B. Dashboard Insights Widget**

1. Go to **Dashboard**
2. Scroll to **"AI Insights"** section
3. Should show pattern insights like:
   - "You complete 'Morning workout' most often on Mondays"
   - "You're on a 5-day streak with 'Morning workout'"
   - Confidence scores and suggestions

### **C. Admin ML Testing Page**

1. Go to **Admin** page
2. Scroll to **"ML Predictions Testing"**
3. Enter a habit name: "Exercise"
4. Click **"Test ML Prediction"**
5. Should show:
   - Probability: 0.75
   - Confidence: 0.82
   - Recommendation: "High probability - keep it up!"

### **D. Finance Module**

1. Go to **Finance** page
2. Add a transaction manually
3. Check the monthly budget tracker
4. Test receipt scanning if you have a receipt image

### **E. Medications Module**

1. Go to **Medications** page
2. Add a medication manually
3. Test prescription scanning if you have a prescription image
4. Check medication timers

---

## 🐛 If Build Fails

### **Error: Out of Memory**

If you see "Killed" or memory errors during build:

```bash
# Build services one at a time
docker-compose -f docker-compose.test.yml build gateway
docker-compose -f docker-compose.test.yml build ai_brain
docker-compose -f docker-compose.test.yml build habits
docker-compose -f docker-compose.test.yml build ml_engine
docker-compose -f docker-compose.test.yml build frontend
# ... continue for other services

# Then start all at once
docker-compose -f docker-compose.test.yml up
```

### **Error: Python Build Takes Too Long**

If Python package installation is slow:

```bash
# Use cached wheels to speed up builds
export PIP_NO_CACHE_DIR=0
docker-compose -f docker-compose.test.yml build --parallel
```

### **Error: Frontend Build Fails**

If React build fails with memory error:

```bash
# Build frontend with limited memory
cd "frontend/kilo-react-frontend"
export NODE_OPTIONS="--max-old-space-size=2048"
npm install --legacy-peer-deps
npm run build

# Then copy to nginx manually
docker-compose -f docker-compose.test.yml up frontend
```

---

## 📈 Performance Expectations

### **Your 2012 System:**
- **ML predictions**: ~200-500ms (scikit-learn RandomForest)
- **Pattern detection**: ~500ms-1s (analyzing habits data)
- **Memory search**: ~100-200ms for 1000 memories
- **Frontend load**: 2-3 seconds initial load
- **Page navigation**: Instant (React Router)

### **For Comparison (Beelink SER7-9):**
- **ML predictions**: ~50-100ms
- **Pattern detection**: ~100-200ms
- **Memory search**: ~50ms for 1000 memories
- **Frontend load**: <1 second
- **Page navigation**: Instant

Your system will be **2-5x slower** than the Beelink, but **totally usable** for testing!

---

## 🔧 Optimization Tips for Old Hardware

### **1. Reduce Docker Memory Limit**

Edit `/etc/docker/daemon.json`:
```json
{
  "default-shm-size": "512M",
  "memory": "8G"
}
```

Then restart Docker:
```bash
sudo systemctl restart docker
```

### **2. Use Swap if Needed**

Check swap:
```bash
free -h
```

If you don't have swap, create it:
```bash
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### **3. Close Unnecessary Programs**

Before testing, close:
- Chrome/Firefox (except one tab for testing)
- IDEs (VSCode, PyCharm)
- Spotify, Slack, Discord, etc.

---

## ✅ Success Checklist

- [ ] All 9 services started successfully
- [ ] Frontend loads at http://localhost:3000
- [ ] Can create and complete habits
- [ ] ML predictions show up in habit cards
- [ ] Dashboard insights widget displays patterns
- [ ] Admin testing page works
- [ ] Can add medications and transactions
- [ ] No errors in `docker-compose logs`

---

## 🚨 Stop Services

When done testing:

```bash
# Stop all services
docker-compose -f docker-compose.test.yml down

# Stop and remove volumes (clean slate for next test)
docker-compose -f docker-compose.test.yml down -v
```

---

## 🎉 Next Steps After Testing

Once you've verified everything works on your 2012 system:

1. **Deploy to Beelink SER7-9** using full `docker-compose.yml` (with Ollama)
2. **Download models** using `download_models.sh` script
3. **Transfer to air-gapped Beelink** and enjoy full AI features

Your 2012 system proves the ML features work, then the Beelink gives you the full experience with LLM chat!

---

## 📞 Troubleshooting

If you hit issues:

1. Check logs: `docker-compose -f docker-compose.test.yml logs -f`
2. Check service status: `docker-compose -f docker-compose.test.yml ps`
3. Check RAM usage: `free -h`
4. Check Docker disk usage: `docker system df`
5. Clean up old images: `docker system prune -a`

---

**Your 2012 system is perfect for testing! The ML features are lightweight scikit-learn models that run fast even on old CPUs. The heavy stuff (Ollama LLM) is optional for testing.**
