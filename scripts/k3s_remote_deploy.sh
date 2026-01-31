#!/usr/bin/env bash
set -euo pipefail

# k3s_remote_deploy.sh
# Usage: ./k3s_remote_deploy.sh [--skip-prometheus] [--prom-token-file /path/to/token]
# This script is intended to be run directly on the K3s host (or via an SSH session).
# It will:
#  - verify kubectl and helm are available
#  - run k3s/deploy.sh (honoring SKIP_PROMETHEUS env or --skip-prometheus)
#  - wait for key deployments to rollout
#  - collect pod status, descriptions and logs under /tmp/k3s-deploy-<timestamp>/
#  - create a zip archive in /tmp and print its path

NS=kilo-guardian
SKIP_PROM=false
PROM_TOKEN_FILE=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --skip-prometheus) SKIP_PROM=true; shift ;;
    --prom-token-file) PROM_TOKEN_FILE="$2"; shift 2 ;;
    -h|--help) grep '^#' "$0" | sed 's/^# //'; exit 0 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

echo "Running remote deploy helper"

echo "Checking kubectl..."
if ! command -v kubectl >/dev/null 2>&1; then
  echo "ERROR: kubectl not found. Install kubectl on the host and re-run." >&2
  exit 2
fi

echo "Checking helm... (Helm required for Prometheus install)"
if ! command -v helm >/dev/null 2>&1; then
  echo "WARNING: helm not found. Prometheus install will be skipped unless you have preinstalled Helm or set SKIP_PROMETHEUS."
fi

if [ -n "$PROM_TOKEN_FILE" ]; then
  if [ -f "$PROM_TOKEN_FILE" ]; then
    echo "Creating monitoring secret 'gateway-admin-token' from $PROM_TOKEN_FILE"
    kubectl -n monitoring create secret generic gateway-admin-token --from-file=token="$PROM_TOKEN_FILE" --dry-run=client -o yaml | kubectl apply -f - || true
  else
    echo "WARNING: PROM token file $PROM_TOKEN_FILE not found, skipping creation" >&2
  fi
fi

# Export SKIP_PROMETHEUS env for the deploy.sh script
if [ "$SKIP_PROM" = true ]; then
  export SKIP_PROMETHEUS=true
fi

echo "Running k3s/deploy.sh"
chmod +x ./k3s/deploy.sh
./k3s/deploy.sh || (echo "Deploy script failed; continuing to collect diagnostics" && true)

# Wait for key deployments (gateway, ai-brain, frontend) up to 2 minutes
echo "Waiting for rollouts (gateway, ai-brain, frontend)"
for d in kilo-gateway kilo-ai-brain kilo-frontend; do
  echo "Waiting for deployment $d..."
  if ! kubectl -n ${NS} rollout status deployment/$d --timeout=120s; then
    echo "Rollout did not finish for $d" >&2
  fi
done

TS=$(date +%Y%m%dT%H%M%S)
OUTDIR="/tmp/k3s-deploy-$TS"
mkdir -p "$OUTDIR"

# Collect resources
kubectl -n ${NS} get deployments,svc,ingress,pods -o wide > "$OUTDIR/resources.txt" || true
kubectl -n monitoring get secrets || true > "$OUTDIR/monitoring-secrets.txt" || true

# Describe failing pods and collect logs
PODS=$(kubectl -n ${NS} get pods -o name || true)
for p in $PODS; do
  echo "Describing $p" >> "$OUTDIR/pod_descriptions.txt"
  kubectl -n ${NS} describe $p >> "$OUTDIR/pod_descriptions.txt" 2>&1 || true
  NAME=$(basename $p)
  mkdir -p "$OUTDIR/logs/$NAME"
  # collect last 500 lines of each container
  CONTAINERS=$(kubectl -n ${NS} get $p -o jsonpath='{.spec.containers[*].name}') || true
  for c in $CONTAINERS; do
    kubectl -n ${NS} logs $p -c $c --tail=500 > "$OUTDIR/logs/${NAME}/${c}.log" 2>&1 || true
  done
done

# Additional global diagnostics
kubectl cluster-info dump --output-directory="$OUTDIR/cluster-dump" || true

# Package results
ZIPPATH="/tmp/k3s-deploy-$TS.zip"
( cd /tmp && zip -r "$ZIPPATH" "k3s-deploy-$TS" )

echo "Diagnostics archived to: $ZIPPATH"

echo
echo "Next steps:" 
echo " - Download the zip file via scp: scp user@host:$ZIPPATH ./"
echo " - Inspect logs in 'logs/' and 'pod_descriptions.txt' to find failures"

exit 0
