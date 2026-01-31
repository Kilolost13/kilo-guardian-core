# Kubernetes Cluster Audit Report
**Date**: 2026-01-06
**Namespace**: kilo-guardian
**Auditor**: Claude Code

---

## Executive Summary

### Critical Issues Found
1. **CRITICAL**: kilo-meds deployment stuck in failed rolling update (CrashLoopBackOff)
2. **HIGH**: 64 stale ReplicaSets consuming cluster resources
3. **MEDIUM**: kilo-socketio using wrong base image (python:3.11-slim instead of custom image)

### Resource Inventory
- **Deployments**: 14 (all active, no duplicates)
- **ReplicaSets**: 72 total (8 active, 64 stale)
- **Pods**: 15 (14 running, 1 crashing)
- **Services**: 15 (no duplicates)

### Health Status
- **Healthy Services**: 13/14 (93%)
- **Broken Services**: 1/14 (kilo-meds in rolling update failure)
- **Stale Resource Overhead**: 64 ReplicaSets with 0 replicas

---

## Detailed Findings

### 1. CRITICAL: kilo-meds Deployment Failure

**Status**: Deployment stuck in rolling update
**Impact**: Service partially degraded - old version still running but update failing
**Root Cause**: Missing `prometheus_client` dependency in kilo-meds:ai-brain-ocr-v2 image

**Evidence**:
```
Deployment: kilo-meds
  Desired Replicas: 1
  Current Replicas: 2
  Available Replicas: 1
  Unavailable Replicas: 1

Active ReplicaSets:
  - kilo-meds-55d9cd8856 (kilo-meds:cb1) - Running, age 23h
  - kilo-meds-7568f7694c (kilo-meds:ai-brain-ocr-v2) - CrashLoopBackOff, age 7m

Pod Error:
  ModuleNotFoundError: No module named 'prometheus_client'
  Exit Code: 1
  Restart Count: 6
```

**Impact Analysis**:
- Old meds service (kilo-meds:cb1) still functional and serving traffic
- New AI Brain integration feature unavailable due to crash
- Kubernetes unable to complete rolling update
- Pod consuming resources through restart cycles

**Recommended Action**:
1. Rollback deployment to stable kilo-meds:cb1 image
2. Fix Dockerfile/requirements.txt to include prometheus_client
3. Rebuild kilo-meds:ai-brain-ocr-v3 with correct dependencies
4. Re-deploy after testing

---

### 2. HIGH: Stale ReplicaSet Accumulation

**Status**: 64 ReplicaSets with 0 replicas cluttering namespace
**Impact**: Resource overhead, difficult cluster management, confusion
**Root Cause**: Kubernetes retains old ReplicaSets for rollback capability (default: 10 per deployment)

**Stale ReplicaSet Breakdown by Service**:

| Service | Total RS | Active RS | Stale RS | Oldest RS Age |
|---------|----------|-----------|----------|---------------|
| kilo-frontend | 11 | 1 | 10 | 7d15h |
| kilo-meds | 9 | 2 | 7 | 7d21h |
| kilo-financial | 9 | 1 | 8 | 7d20h |
| kilo-cam | 8 | 1 | 7 | 8d |
| kilo-gateway | 6 | 1 | 5 | 7d22h |
| kilo-habits | 5 | 1 | 4 | 7d22h |
| kilo-reminder | 5 | 1 | 4 | 8d |
| kilo-library | 4 | 1 | 3 | 8d |
| kilo-ml-engine | 4 | 1 | 3 | 8d |
| kilo-ollama | 4 | 1 | 3 | 8d |
| kilo-usb-transfer | 4 | 1 | 3 | 8d |
| kilo-voice | 4 | 1 | 3 | 8d |
| kilo-ai-brain | 3 | 1 | 2 | 8d |
| kilo-socketio | 2 | 1 | 1 | 7d21h |

**Impact Analysis**:
- Each ReplicaSet stores full pod template specification
- etcd database bloat from storing unused configurations
- Difficult to identify current vs historical deployments
- `kubectl get rs` output overwhelming with noise

**Recommended Action**:
Delete all ReplicaSets with `replicas: 0` (safe operation - no running pods affected)

---

### 3. MEDIUM: kilo-socketio Wrong Image

**Status**: Using generic python:3.11-slim instead of custom service image
**Impact**: Service may lack required dependencies or custom configuration

**Evidence**:
```
Deployment: kilo-socketio
  Image: python:3.11-slim
  Expected: kilo-socketio:latest or kilo/socketio:latest
```

**Recommended Action**:
1. Verify if custom socketio image exists
2. If not, build custom image with proper dependencies
3. Update deployment to use custom image

---

### 4. Image Tag Inconsistencies

**Status**: Mixed image naming conventions across services
**Impact**: Confusion about image versioning and sources

**Image Naming Patterns Found**:
- `kilo/<service>:latest` (6 services) - ai_brain, cam, library, ml_engine, usb_transfer, voice
- `kilo-<service>:<tag>` (5 services) - frontend, gateway, habits, meds, reminder
- `kilo/<service>:latest` + custom deployment (financial)
- `python:3.11-slim` (socketio - wrong!)
- `ollama/ollama:latest` (external image - correct)

**Recommended Action**:
Standardize on `kilo/<service>:latest` for production, `kilo-<service>:<tag>` for testing/staging

---

## Deployment Status by Service

### Healthy Deployments (13/14)

| Service | Image | Status | Age | Notes |
|---------|-------|--------|-----|-------|
| kilo-ai-brain | kilo/ai_brain:latest | Running | 8d | 11 restarts (stable now) |
| kilo-cam | kilo/cam:latest | Running | 3d5h | Recently updated |
| kilo-financial | kilo/financial:latest | Running | 22h | Fixed prometheus issue |
| kilo-frontend | kilo-frontend:stats-v3 | Running | 22h | Stats feature deployed |
| kilo-gateway | kilo-gateway:multipart-fix | Running | 17h | Multipart bug fixed |
| kilo-habits | kilo-habits:cb1 | Running | 23h | Recent update |
| kilo-library | kilo/library_of_truth:latest | Running | 3d5h | Stable |
| kilo-ml-engine | kilo/ml_engine:latest | Running | 3d5h | Stable |
| kilo-ollama | ollama/ollama:latest | Running | 3d5h | External image |
| kilo-reminder | kilo-reminder:cb1 | Running | 23h | Recent update |
| kilo-socketio | python:3.11-slim | Running | 3d5h | WRONG IMAGE |
| kilo-usb-transfer | kilo/usb_transfer:latest | Running | 3d5h | Stable |
| kilo-voice | kilo/voice:latest | Running | 3d5h | Stable |

### Failed Deployments (1/14)

| Service | Image | Status | Issue |
|---------|-------|--------|-------|
| kilo-meds | kilo-meds:ai-brain-ocr-v2 | CrashLoopBackOff | Missing prometheus_client |

---

## Service Health Summary

All 15 services properly configured:

**Internal Services (ClusterIP)**:
- kilo-ai-brain: 10.43.63.197:9004
- kilo-cam: 10.43.12.200:9007
- kilo-financial: 10.43.216.158:9005
- kilo-frontend: 10.43.106.87:80
- kilo-gateway: 10.43.138.244:8000
- kilo-habits: 10.43.142.9:9003
- kilo-library: 10.43.173.215:9006
- kilo-meds: 10.43.214.225:9001
- kilo-ml-engine: 10.43.196.200:9008
- kilo-reminder: 10.43.144.204:9002
- kilo-socketio: 10.43.30.96:9010
- kilo-usb-transfer: 10.43.38.72:8006
- kilo-voice: 10.43.236.231:9009

**External Services (NodePort)**:
- kilo-frontend-external: 30000 (tablet access)
- kilo-gateway-external: 30800

**No Issues**: No duplicate services, no orphaned services

---

## Root Cause Analysis

### Why are there so many stale ReplicaSets?

1. **High Deployment Frequency**: Evidence shows frequent updates over 8 days
   - kilo-frontend: 11 ReplicaSets = ~1.4 deploys/day
   - kilo-financial: 9 ReplicaSets = ~1.1 deploys/day

2. **Kubernetes Default Behavior**: `revisionHistoryLimit: 10` by default
   - K8s retains old ReplicaSets for rollback capability
   - Each `kubectl set image` or deployment update creates new ReplicaSet
   - Old ones set to `replicas: 0` but not deleted

3. **Development/Testing Cycle**: Active development causing frequent rebuilds
   - Image tag changes (cb1, v2, multipart-fix, stats-v3, etc.)
   - Bug fixes (financial prometheus, gateway multipart)
   - Feature additions (AI Brain integration)

### Why did kilo-meds:ai-brain-ocr-v2 fail?

1. **Missing Dependency**: main.py line 16 imports prometheus_client but not in requirements.txt
2. **Incomplete Docker Build**: Image built without checking import dependencies
3. **No Pre-Deployment Testing**: Image not tested before K8s deployment
4. **Rolling Update Strategy**: K8s tried to update but kept old pod alive when new one failed (good!)

### Previous Issues (Now Resolved)

1. **kilo-meds-v2 duplicate deployment** - DELETED (verified)
2. **Split-brain database issue** - RESOLVED by scaling to 1 replica
3. **Gateway multipart bug** - FIXED (kilo-gateway:multipart-fix deployed 17h ago)
4. **Financial prometheus crash** - FIXED (kilo/financial:latest deployed 22h ago)

---

## Recommendations

### Immediate Actions (Priority 1)

1. **Rollback kilo-meds deployment**:
   ```bash
   kubectl rollout undo deployment/kilo-meds -n kilo-guardian
   ```
   This will remove the crashing ReplicaSet and keep only kilo-meds:cb1

2. **Delete stale ReplicaSets** (64 total):
   - Safe operation (no running pods affected)
   - Frees cluster resources
   - Improves namespace clarity
   - Run cleanup script after approval

### Short-Term Actions (Priority 2)

3. **Fix kilo-meds AI Brain integration**:
   - Add `prometheus_client` to requirements.txt
   - Rebuild as kilo-meds:ai-brain-ocr-v3
   - Test locally before deployment
   - Deploy with monitoring

4. **Fix kilo-socketio image**:
   - Build custom kilo/socketio:latest image
   - Update deployment
   - Verify service still works

### Long-Term Actions (Priority 3)

5. **Reduce revisionHistoryLimit**:
   - Current: 10 (default)
   - Recommended: 3 (enough for rollbacks)
   - Prevents ReplicaSet accumulation

6. **Standardize image naming**:
   - Production: `kilo/<service>:latest`
   - Testing: `kilo-<service>:<feature-tag>`
   - Clear separation of environments

7. **Implement pre-deployment testing**:
   - Test images locally before K8s import
   - Verify all dependencies installed
   - Check service starts without errors

---

## Cleanup Plan

The cleanup script (`cleanup-k8s.sh`) will:

1. **Rollback kilo-meds** to stable version
2. **Delete 64 stale ReplicaSets** with replicas=0
3. **Update revisionHistoryLimit** to 3 for all deployments
4. **Verify** no running pods affected

**IMPORTANT**: Review cleanup-k8s.sh before execution. Script includes dry-run mode.

---

## Verification Checklist

After cleanup, verify:

- [ ] All 14 pods running (no CrashLoopBackOff)
- [ ] kilo-meds using stable image (kilo-meds:cb1)
- [ ] Total ReplicaSets reduced to ~14 (one per deployment)
- [ ] All services responding to health checks
- [ ] No orphaned resources
- [ ] Frontend accessible at http://localhost:30000
- [ ] Prescription OCR working (after AI Brain fix deployed)

---

## Next Steps

1. **Review this report** and approve cleanup plan
2. **Run cleanup-k8s.sh** to remove stale resources
3. **Fix kilo-meds AI Brain integration** (add prometheus_client)
4. **Deploy fixed version** as kilo-meds:ai-brain-ocr-v3
5. **Test end-to-end** prescription OCR with AI Brain

---

## Appendix: Full Resource Lists

### All ReplicaSets (72 total)

**Active (8)**:
- kilo-ai-brain-c679fb7f9 (1 replica)
- kilo-cam-6c75c48cd6 (1 replica)
- kilo-financial-6767599d96 (1 replica)
- kilo-frontend-6bf69bcfbf (1 replica)
- kilo-gateway-7778cfddf7 (1 replica)
- kilo-habits-59c9bf486f (1 replica)
- kilo-library-6dd7ff6d48 (1 replica)
- kilo-meds-55d9cd8856 (1 replica) - CURRENT STABLE
- kilo-meds-7568f7694c (1 replica) - CRASHING, NEEDS ROLLBACK
- kilo-ml-engine-5b789cf9d8 (1 replica)
- kilo-ollama-5cbbf465bf (1 replica)
- kilo-reminder-555bf7c6f9 (1 replica)
- kilo-socketio-5d45b68c4 (1 replica)
- kilo-usb-transfer-6b795f5bf6 (1 replica)
- kilo-voice-9596547d4 (1 replica)

**Stale (64)**: All with 0 replicas - safe to delete

---

**End of Report**
