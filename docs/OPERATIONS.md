# Kilo Guardian Operations Guide
**Daily operations, monitoring, and maintenance for Kilo Guardian**

Last Updated: 2026-01-04

---

## Quick Reference

### System Status Check
```bash
# One command to check everything
kubectl get pods,svc -n kilo-guardian
```

### Access URLs
- **Frontend:** http://localhost:30000
- **Gateway API:** http://localhost:30800
- **From Tablet:** Via SSH tunnel (see [TABLET_ACCESS.md](TABLET_ACCESS.md))

---

## Daily Operations

### 1. Check System Health

#### View All Pods
```bash
kubectl get pods -n kilo-guardian
```

**Expected Output:** All pods should show `1/1 READY` and `Running` status.

#### Check Services
```bash
kubectl get svc -n kilo-guardian
```

**Expected:** 15 services listed with ClusterIP or NodePort types.

#### Quick Health Test
```bash
# Test frontend
curl -s -o /dev/null -w "Frontend: %{http_code}\n" http://localhost:30000

# Test gateway
curl -s -o /dev/null -w "Gateway: %{http_code}\n" http://localhost:30800/meds/
```

**Expected:** Both return HTTP 200.

---

### 2. View Logs

#### Real-Time Logs (Follow Mode)
```bash
# Gateway logs
kubectl logs -f deployment/kilo-gateway -n kilo-guardian

# Specific service logs
kubectl logs -f deployment/kilo-meds -n kilo-guardian

# AI Brain logs
kubectl logs -f deployment/kilo-ai-brain -n kilo-guardian
```

Press `Ctrl+C` to stop following.

#### Recent Logs (Last 50 Lines)
```bash
kubectl logs deployment/kilo-gateway -n kilo-guardian --tail=50
```

#### Logs with Timestamps
```bash
kubectl logs deployment/kilo-gateway -n kilo-guardian --timestamps --tail=100
```

#### Previous Container Logs (After Restart)
```bash
kubectl logs deployment/kilo-gateway -n kilo-guardian --previous
```

---

### 3. Restart Services

#### Restart Single Service
```bash
# Restart medications service
kubectl rollout restart deployment/kilo-meds -n kilo-guardian

# Restart gateway
kubectl rollout restart deployment/kilo-gateway -n kilo-guardian

# Restart frontend
kubectl rollout restart deployment/kilo-frontend -n kilo-guardian
```

#### Restart All Services
```bash
kubectl rollout restart deployment -n kilo-guardian
```

**Note:** K3s will perform rolling restarts with zero downtime.

#### Check Restart Status
```bash
kubectl rollout status deployment/kilo-meds -n kilo-guardian
```

---

### 4. Scale Services

#### Scale Up (Increase Replicas)
```bash
# Scale ML engine to 2 replicas for heavy processing
kubectl scale deployment/kilo-ml-engine --replicas=2 -n kilo-guardian
```

#### Scale Down (Reduce Replicas)
```bash
# Scale back to 1 replica
kubectl scale deployment/kilo-ml-engine --replicas=1 -n kilo-guardian
```

#### Check Current Scale
```bash
kubectl get deployment/kilo-ml-engine -n kilo-guardian
```

---

### 5. Access Pod Shell

#### Execute Shell in Pod
```bash
# Gateway pod
kubectl exec -it deployment/kilo-gateway -n kilo-guardian -- /bin/sh

# Frontend pod
kubectl exec -it deployment/kilo-frontend -n kilo-guardian -- /bin/sh
```

**Useful Commands Inside Pod:**
```bash
# Check environment variables
env | grep KILO

# Test network connectivity
wget -O- http://kilo-meds:9001

# View local files
ls -la /app/
```

Type `exit` to leave the pod shell.

---

### 6. Monitor Resource Usage

#### Pod Resource Usage
```bash
kubectl top pods -n kilo-guardian
```

**Shows:** CPU and memory usage per pod.

#### Node Resource Usage
```bash
kubectl top nodes
```

**Note:** Requires metrics-server to be installed.

#### Pod Resource Limits
```bash
kubectl describe deployment/kilo-gateway -n kilo-guardian | grep -A 5 "Limits"
```

---

### 7. Troubleshooting

#### Pod Not Starting
```bash
# 1. Check pod status
kubectl get pod -n kilo-guardian

# 2. Describe pod for events
kubectl describe pod <pod-name> -n kilo-guardian

# 3. Check logs
kubectl logs <pod-name> -n kilo-guardian

# 4. Check events
kubectl get events -n kilo-guardian --sort-by='.lastTimestamp' | tail -20
```

#### Service Not Accessible
```bash
# 1. Verify service exists
kubectl get svc/kilo-gateway -n kilo-guardian

# 2. Check endpoints
kubectl get endpoints -n kilo-guardian

# 3. Test from another pod
kubectl exec deployment/kilo-frontend -n kilo-guardian -- wget -O- http://kilo-gateway:8000/

# 4. Check firewall (if NodePort)
sudo ufw status
```

#### High Memory Usage
```bash
# 1. Check which pod is using memory
kubectl top pods -n kilo-guardian

# 2. Restart the pod
kubectl rollout restart deployment/<service-name> -n kilo-guardian

# 3. Check logs for memory leaks
kubectl logs deployment/<service-name> -n kilo-guardian | grep -i memory
```

#### Pod Stuck in CrashLoopBackOff
```bash
# 1. Check logs
kubectl logs <pod-name> -n kilo-guardian --previous

# 2. Describe pod
kubectl describe pod <pod-name> -n kilo-guardian

# 3. Delete pod to force recreation
kubectl delete pod <pod-name> -n kilo-guardian
```

---

### 8. Database Operations

#### Check Database Pods
All services use SQLite databases stored in their pods. No separate database pod.

#### Backup Database (From Within Pod)
```bash
# Example: Backup medications database
kubectl exec deployment/kilo-meds -n kilo-guardian -- tar -czf /tmp/meds-backup.tar.gz /app/data/

# Copy backup to local machine
kubectl cp kilo-guardian/<pod-name>:/tmp/meds-backup.tar.gz ./meds-backup.tar.gz
```

#### Restore Database
```bash
# Copy backup to pod
kubectl cp ./meds-backup.tar.gz kilo-guardian/<pod-name>:/tmp/

# Extract in pod
kubectl exec deployment/kilo-meds -n kilo-guardian -- tar -xzf /tmp/meds-backup.tar.gz -C /
```

---

### 9. Update Services

#### Update Service Image
```bash
# Set new image for a service
kubectl set image deployment/kilo-frontend frontend=my-repo/kilo-frontend:v2.0 -n kilo-guardian

# Check rollout status
kubectl rollout status deployment/kilo-frontend -n kilo-guardian
```

#### Rollback to Previous Version
```bash
# Undo last deployment
kubectl rollout undo deployment/kilo-frontend -n kilo-guardian

# Rollback to specific revision
kubectl rollout undo deployment/kilo-frontend --to-revision=2 -n kilo-guardian
```

#### View Rollout History
```bash
kubectl rollout history deployment/kilo-frontend -n kilo-guardian
```

---

### 10. Network Testing

#### Test Pod-to-Pod Communication
```bash
# From gateway, test meds service
kubectl exec deployment/kilo-gateway -n kilo-guardian -- curl -s http://kilo-meds:9001/

# Test all services (run from gateway pod)
kubectl exec deployment/kilo-gateway -n kilo-guardian -- sh -c '
  for svc in kilo-meds:9001 kilo-reminder:9002 kilo-habits:9003 kilo-ai-brain:9004; do
    echo "Testing $svc..."
    curl -s -o /dev/null -w "%{http_code}\n" http://$svc/ || echo "FAILED"
  done
'
```

#### DNS Resolution Test
```bash
# Test if service DNS is working
kubectl exec deployment/kilo-gateway -n kilo-guardian -- nslookup kilo-meds
```

#### Port Forward for Local Testing
```bash
# Forward kilo-meds to localhost:9001
kubectl port-forward deployment/kilo-meds 9001:9001 -n kilo-guardian

# Now access at http://localhost:9001
# Press Ctrl+C to stop
```

---

### 11. Configuration Management

#### View ConfigMaps
```bash
kubectl get configmap -n kilo-guardian
```

#### Edit ConfigMap
```bash
kubectl edit configmap <configmap-name> -n kilo-guardian
```

#### View Secrets
```bash
kubectl get secrets -n kilo-guardian
```

#### Create Secret
```bash
kubectl create secret generic my-secret \
  --from-literal=api-key=abc123 \
  -n kilo-guardian
```

---

### 12. Cluster-Wide Operations

#### Check K3s Status
```bash
sudo systemctl status k3s
```

#### View All Resources
```bash
kubectl get all -n kilo-guardian
```

#### Delete All Resources (DANGER - USE WITH CAUTION)
```bash
# This will delete EVERYTHING in the namespace
kubectl delete all --all -n kilo-guardian
```

#### Recreate from Manifests
```bash
kubectl apply -f k3s/ -n kilo-guardian
```

---

## Common Scenarios

### Scenario 1: Service is Down

1. **Check if pod is running:**
   ```bash
   kubectl get pods -n kilo-guardian | grep kilo-meds
   ```

2. **View recent logs:**
   ```bash
   kubectl logs deployment/kilo-meds -n kilo-guardian --tail=50
   ```

3. **Restart the service:**
   ```bash
   kubectl rollout restart deployment/kilo-meds -n kilo-guardian
   ```

4. **Verify it's back up:**
   ```bash
   curl http://localhost:30800/meds/
   ```

---

### Scenario 2: Frontend Won't Load

1. **Check frontend pod:**
   ```bash
   kubectl get pod -l app=kilo-frontend -n kilo-guardian
   ```

2. **Test frontend directly:**
   ```bash
   curl http://localhost:30000
   ```

3. **Check frontend service:**
   ```bash
   kubectl get svc kilo-frontend-external -n kilo-guardian
   ```

4. **Restart frontend:**
   ```bash
   kubectl rollout restart deployment/kilo-frontend -n kilo-guardian
   ```

---

### Scenario 3: Database Corruption

1. **Identify the affected service**

2. **Access the pod shell:**
   ```bash
   kubectl exec -it deployment/kilo-meds -n kilo-guardian -- /bin/sh
   ```

3. **Check database file:**
   ```bash
   ls -lh /app/data/*.db
   ```

4. **If corrupted, restore from backup or delete pod:**
   ```bash
   kubectl delete pod <pod-name> -n kilo-guardian
   ```

---

### Scenario 4: Tablet Can't Connect

1. **Check SSH is running on server:**
   ```bash
   sudo systemctl status ssh
   ```

2. **Verify NodePort services:**
   ```bash
   kubectl get svc -n kilo-guardian | grep NodePort
   ```

3. **Test locally first:**
   ```bash
   curl http://localhost:30000
   ```

4. **Check firewall:**
   ```bash
   sudo ufw status
   ```

---

## Maintenance Tasks

### Weekly Maintenance

1. **Check pod health:**
   ```bash
   kubectl get pods -n kilo-guardian
   ```

2. **Review logs for errors:**
   ```bash
   kubectl logs deployment/kilo-gateway -n kilo-guardian | grep -i error
   ```

3. **Check disk usage:**
   ```bash
   df -h
   ```

4. **Verify backups exist**

---

### Monthly Maintenance

1. **Update documentation**
2. **Review resource usage trends**
3. **Update service images (if needed)**
4. **Test disaster recovery procedures**
5. **Clean old container images:**
   ```bash
   docker system prune -a
   ```

---

## Emergency Procedures

### Complete System Restart

```bash
# 1. Stop K3s
sudo systemctl stop k3s

# 2. Wait 30 seconds
sleep 30

# 3. Start K3s
sudo systemctl start k3s

# 4. Wait for pods to start (2-3 minutes)
watch kubectl get pods -n kilo-guardian

# 5. Verify services
curl http://localhost:30000
```

---

### Complete System Reset (NUCLEAR OPTION)

**⚠️ WARNING: This deletes ALL data!**

```bash
# 1. Delete namespace (deletes all pods, services, data)
kubectl delete namespace kilo-guardian

# 2. Recreate namespace
kubectl create namespace kilo-guardian

# 3. Redeploy everything
kubectl apply -f k3s/ -n kilo-guardian
```

---

## Monitoring & Alerts

### Set Up Basic Monitoring

```bash
# Watch pod status in real-time
watch -n 5 kubectl get pods -n kilo-guardian

# Monitor resource usage
watch -n 10 kubectl top pods -n kilo-guardian
```

### Log Monitoring

```bash
# Follow all logs
kubectl logs -f -l namespace=kilo-guardian --all-containers=true
```

---

## Best Practices

1. **Always check logs before restarting** - Understand the problem first
2. **Use rollout restart instead of delete** - Ensures zero downtime
3. **Test locally before restarting production** - Use port-forward
4. **Keep regular backups** - Weekly database backups minimum
5. **Document changes** - Update this guide when you learn new operations
6. **Monitor resource usage** - Prevent issues before they occur
7. **Use descriptive names** - Makes troubleshooting easier

---

## Useful Scripts

Scripts are located in `~/scripts/` on the server:

- **k8s-status.sh** - Quick system status
- **k8s-logs.sh** - View service logs
- **k8s-restart.sh** - Restart a service
- **start-kilo-tunnel.sh** - Auto-reconnecting SSH tunnel

---

## Additional Resources

- [Pod Health Report](POD_HEALTH_REPORT.md) - Current system status
- [Service Communication Test](SERVICE_COMMUNICATION_TEST.md) - Connectivity verification
- [Tablet Access Guide](TABLET_ACCESS.md) - Remote access setup
- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Initial deployment
- [K3s Access Guide](K3S_ACCESS_GUIDE.md) - Kubernetes administration

---

**Need Help?**

1. Check this guide first
2. View service logs: `kubectl logs deployment/<service> -n kilo-guardian`
3. Check system status: [POD_HEALTH_REPORT.md](POD_HEALTH_REPORT.md)
4. Review recent events: `kubectl get events -n kilo-guardian`

---

**Kilo Guardian Operations - Keep it running smoothly! 🚀**
