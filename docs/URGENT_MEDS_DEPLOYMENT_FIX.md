# URGENT: Meds OCR Deployment Fix
**Date:** 2026-01-05
**Status:** ⚠️ REQUIRES MANUAL EXECUTION (sudo needed)

---

## Problem Summary

### Issue Discovered
- **TWO meds pods** exist: `kilo-meds` and `kilo-meds-v2`
- `kilo-meds`: Using old `kilo-meds:v2` image (no async OCR)
- `kilo-meds-v2`: Using base `python:3.11-slim` image (not our code!)
- Frontend POST `/extract` hitting **OLD pod** without async OCR code
- Result: Requests fail, no `job_id` returned

### Current State
```
kilo-meds deployment:
  Image: kilo-meds:v2 (OLD - no async OCR)

kilo-meds-v2 deployment:
  Image: python:3.11-slim (BASE IMAGE - not built!)
```

---

## Solution Prepared

### What Was Done
✅ Updated `services/meds/main.py` with async OCR code
✅ Built new Docker image: `kilo-meds:ocr-async`
✅ Tagged as: `kilo-meds:v2` (to replace old version)
✅ Created import script: `/home/kilo/import-meds-to-k3s.sh`

### What Needs Manual Execution
⚠️ **Requires sudo password** to import image into K3s

---

## IMMEDIATE FIX (Run This Now)

### Option 1: Run Import Script (Recommended)

```bash
cd /home/kilo
sudo bash import-meds-to-k3s.sh
```

**What the script does:**
1. Saves `kilo-meds:v2` Docker image to tar
2. Imports into K3s containerd (requires sudo)
3. Restarts `kilo-meds` deployment
4. Updates `kilo-meds-v2` to use `kilo-meds:v2` image
5. Verifies both pods are running

**Expected output:**
```
================================================
Importing Meds Image into K3s
================================================

Step 1: Saving Docker image kilo-meds:v2...
Step 2: Importing into K3s containerd...
Step 3: Verifying import...
Step 4: Cleaning up temp file...

✅ Import Complete!

Restarting kilo-meds deployment...
deployment.apps/kilo-meds restarted
Waiting for deployment "kilo-meds" rollout to finish...
deployment "kilo-meds" successfully rolled out

Updating kilo-meds-v2 to use kilo-meds:v2 image...
deployment.apps/kilo-meds-v2 image updated
Waiting for deployment "kilo-meds-v2" rollout to finish...
deployment "kilo-meds-v2" successfully rolled out

✅ Both deployments updated!

Verifying pods...
kilo-meds-xxxxx            1/1     Running   0          30s
kilo-meds-v2-xxxxx         1/1     Running   0          25s
```

---

### Option 2: Manual Steps

If the script fails, run these commands manually:

```bash
# 1. Save Docker image
docker save kilo-meds:v2 -o /tmp/kilo-meds-v2.tar

# 2. Import to K3s (REQUIRES SUDO)
sudo k3s ctr images import /tmp/kilo-meds-v2.tar

# 3. Verify import
sudo k3s ctr images ls | grep kilo-meds

# 4. Restart kilo-meds deployment
kubectl rollout restart deployment/kilo-meds -n kilo-guardian
kubectl rollout status deployment/kilo-meds -n kilo-guardian

# 5. Update kilo-meds-v2 deployment
kubectl set image deployment/kilo-meds-v2 \
  meds-v2=kilo-meds:v2 \
  -n kilo-guardian
kubectl rollout status deployment/kilo-meds-v2 -n kilo-guardian

# 6. Verify both pods running
kubectl get pods -n kilo-guardian | grep meds

# 7. Clean up
rm /tmp/kilo-meds-v2.tar
```

---

## Verification Steps

### 1. Check Both Pods Are Running
```bash
kubectl get pods -n kilo-guardian | grep meds
```

**Expected:**
```
kilo-meds-xxxxx            1/1     Running   0          1m
kilo-meds-v2-xxxxx         1/1     Running   0          1m
```

### 2. Verify Both Pods Have New Image
```bash
kubectl describe pod -n kilo-guardian -l app=kilo-meds | grep Image:
kubectl describe pod -n kilo-guardian -l app=kilo-meds-v2 | grep Image:
```

**Expected:**
```
Image:      kilo-meds:v2
Image:      kilo-meds:v2
```

### 3. Check Logs for OCR Code
```bash
# Get pod name
POD=$(kubectl get pod -n kilo-guardian -l app=kilo-meds -o jsonpath='{.items[0].metadata.name}')

# Check logs
kubectl logs $POD -n kilo-guardian | tail -20
```

**Look for:**
```
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:9001
```

### 4. Test OCR Endpoint Manually
```bash
# Create a test file
echo "test" > /tmp/test.txt

# Test kilo-meds
kubectl exec deployment/kilo-gateway -n kilo-guardian -- \
  curl -s -X POST http://kilo-meds:9001/extract \
    -F "file=@/tmp/test.txt" | jq

# Test kilo-meds-v2
kubectl exec deployment/kilo-gateway -n kilo-guardian -- \
  curl -s -X POST http://kilo-meds-v2:9001/extract \
    -F "file=@/tmp/test.txt" | jq
```

**Expected response (from BOTH):**
```json
{
  "job_id": "abc-123-def-456",
  "status": "pending",
  "message": "Image received. Processing in background...",
  "poll_url": "/extract/abc-123-def-456/status"
}
```

**OLD response (if not updated):**
```json
{
  "id": 1,
  "name": "",
  "schedule": "",
  ...
}
```

---

## Gateway Routing Check

### Which Meds Pod Does Gateway Use?

The gateway service `kilo-gateway` routes to `kilo-meds` Kubernetes service, which load-balances between pods.

```bash
kubectl get svc kilo-meds -n kilo-guardian -o wide
kubectl get endpoints kilo-meds -n kilo-guardian
```

**Check routing:**
```bash
kubectl logs deployment/kilo-gateway -n kilo-guardian --tail=50 | grep meds
```

**Look for:**
```
POST /meds/extract
Proxy OK: POST http://kilo-meds:9001/extract -> 200
```

---

## Testing End-to-End

### From Frontend
1. Open: http://localhost:30000
2. Navigate to Medications page
3. Click "📷 SCAN PRESCRIPTION"
4. Capture test image
5. Watch browser console

**Expected console logs:**
```
[OCR] Job submitted: abc-123-def, polling for results...
[OCR] Poll 1: status=pending
[OCR] Poll 2: status=processing
[OCR] Poll 3: status=completed
```

**Expected UI:**
```
Button: "⏳ SCANNING..."
(wait 15-45 seconds)
Message: "✓ Added [Med Name]!"
```

### Check Meds Service Logs
```bash
kubectl logs deployment/kilo-meds -n kilo-guardian --tail=100
```

**Expected:**
```
[OCR] Saved image for job abc-123-def to /data/prescription_images/abc-123-def.jpg
[OCR] Queued job abc-123-def for processing
[OCR] Starting processing for job abc-123-def
[OCR] Preprocessing image...
[OCR] Running Tesseract OCR...
[OCR] Extracted 247 characters of text
[OCR] Created medication: Lisinopril (ID: 5)
[OCR] Job abc-123-def completed successfully
```

---

## Troubleshooting

### Issue: "Image not found"
```bash
# Verify image exists in Docker
docker images | grep kilo-meds

# Should show:
# kilo-meds  v2  f3d8c34ed4c9  10 hours ago  1.12GB
```

**Fix:** Re-run import script or manual import steps

### Issue: "Pod stuck in ImagePullBackOff"
```bash
kubectl describe pod -n kilo-guardian -l app=kilo-meds | grep -A 10 Events
```

**Fix:** Verify image was imported to K3s:
```bash
sudo k3s ctr images ls | grep kilo-meds
```

### Issue: "Still getting old response (no job_id)"
```bash
# Force delete pods to recreate
kubectl delete pod -n kilo-guardian -l app=kilo-meds
kubectl delete pod -n kilo-guardian -l app=kilo-meds-v2

# Wait for recreation
kubectl wait --for=condition=ready pod -n kilo-guardian -l app=kilo-meds --timeout=120s
kubectl wait --for=condition=ready pod -n kilo-guardian -l app=kilo-meds-v2 --timeout=120s
```

### Issue: "Gateway still timing out"
Check gateway timeout was increased:
```bash
kubectl logs deployment/kilo-gateway -n kilo-guardian | grep -i timeout
```

If gateway not updated, rebuild and deploy gateway too (see docs/OCR_TIMEOUT_FIX.md)

---

## What's in the New Image

### Changes in `services/meds/main.py`

1. **New Model:**
```python
class OcrJob(SQLModel, table=True):
    job_id: str
    status: str  # pending, processing, completed, failed
    image_path: str
    ocr_text: Optional[str]
    result_data: Optional[str]
```

2. **New Endpoints:**
- `POST /extract` - Returns job_id immediately
- `GET /extract/{job_id}/status` - Poll for status
- `GET /extract/{job_id}/result` - Get final result

3. **Background Worker:**
```python
def process_ocr_job(job_id: str):
    # Load image, run OCR, save medication
```

4. **Image Persistence:**
- Images saved to `/data/prescription_images/{uuid}.jpg`
- Retained for debugging and reprocessing

---

## Success Criteria

✅ **Both meds pods running**
✅ **Both using `kilo-meds:v2` image**
✅ **Both respond to `/extract` with `job_id`**
✅ **Frontend successfully scans prescriptions**
✅ **OCR processing completes without timeout**

---

## Current Status

### Completed
✅ Code updated with async OCR
✅ Docker image built
✅ Image tagged as `kilo-meds:v2`
✅ Import script created

### Pending (REQUIRES SUDO)
⚠️ Import image to K3s
⚠️ Restart kilo-meds deployment
⚠️ Update kilo-meds-v2 deployment
⚠️ Verify both pods running with new image

---

## Next Steps

1. **Run import script:**
   ```bash
   sudo bash /home/kilo/import-meds-to-k3s.sh
   ```

2. **Verify deployment:**
   ```bash
   kubectl get pods -n kilo-guardian | grep meds
   ```

3. **Test OCR:**
   - Open frontend
   - Scan prescription
   - Verify success

4. **Check logs:**
   ```bash
   kubectl logs deployment/kilo-meds -n kilo-guardian --tail=50
   ```

---

## Files Modified

### Backend
- `/home/kilo/Desktop/Kilo_Ai_microservice/services/meds/main.py`
  - Added async OCR processing
  - Added job tracking
  - Added image persistence

### Scripts Created
- `/home/kilo/import-meds-to-k3s.sh`
  - Automated import and deployment

### Documentation
- `/home/kilo/Desktop/Kilo_Ai_microservice/docs/OCR_TIMEOUT_FIX.md`
  - Comprehensive OCR fix documentation
- `/home/kilo/Desktop/Kilo_Ai_microservice/docs/URGENT_MEDS_DEPLOYMENT_FIX.md`
  - This file - deployment instructions

---

**Status:** Ready for deployment via `sudo bash /home/kilo/import-meds-to-k3s.sh`

**Priority:** URGENT - OCR not working until both pods updated

**Estimated Time:** 2-3 minutes for import and deployment

---

*Created: 2026-01-05 09:02*
*Kilo Guardian - Prescription OCR Fix*
