#!/usr/bin/env bash
set -euo pipefail

# This deploy script supports two modes:
#  - Local host run (uses default kubeconfig at $HOME/.kube/config)
#  - CI run via KUBECONFIG_BASE64 environment variable (decoded into a temp file)

NS=kilo-guardian

# If KUBECONFIG_BASE64 is set (e.g., provided by GitHub Actions secret) decode it into a temp file
if [ -n "${KUBECONFIG_BASE64:-}" ]; then
  echo "Decoding KUBECONFIG_BASE64 into temporary kubeconfig"
  tmp_kubeconfig=$(mktemp)
  echo "$KUBECONFIG_BASE64" | base64 --decode > "$tmp_kubeconfig"
  export KUBECONFIG="$tmp_kubeconfig"
  echo "Using temporary KUBECONFIG at $KUBECONFIG"
fi

# check cluster reachability
if ! kubectl version --short >/dev/null 2>&1; then
  echo "kubectl cannot reach a cluster. Make sure KUBECONFIG is set or run this script on the host with k3s installed."
  exit 1
fi

echo "Applying namespace and base config..."
kubectl apply -f k3s/namespace.yaml
kubectl apply -f k3s/secret-library-admin.yaml -n ${NS}
kubectl apply -f k3s/configmap.yaml -n ${NS}

echo "Applying core deployments and services..."
kubectl apply -f k3s/deployments-and-services.yaml -n ${NS}
kubectl apply -f k3s/more-services.yaml -n ${NS}

echo "Applying PDBs and HPAs..."
kubectl apply -f k3s/pdbs-and-hpas.yaml -n ${NS}

echo "Applying Ingress..."
kubectl apply -f k3s/ingress.yaml -n ${NS}

echo "Creating placeholder service account secrets for Prometheus scraping (fill in token files manually for air-gapped)..."
# Create placeholder secrets - update token values with actual tokens
kubectl -n monitoring create secret generic gateway-admin-token --from-literal=token=REPLACE_ME || true
kubectl -n monitoring create secret generic ai-brain-metrics-token --from-literal=token=REPLACE_ME || true

# If a token file exists locally, create the secret from it (useful for automated flows)
if [ -f "k3s/prometheus-token.txt" ]; then
  echo "Found k3s/prometheus-token.txt — creating gateway-admin-token secret in 'monitoring' namespace"
  kubectl -n monitoring create secret generic gateway-admin-token --from-file=token=k3s/prometheus-token.txt --dry-run=client -o yaml | kubectl apply -f - || true
fi

# Allow skipping Prometheus install via SKIP_PROMETHEUS env var (useful in CI)
SKIP=${SKIP_PROMETHEUS:-false}
if [ "$SKIP" = "true" ] || [ "$SKIP" = "1" ]; then
  echo "SKIP_PROMETHEUS set - skipping Helm install"
else
  # Install Prometheus stack via Helm if helm is available
  if command -v helm >/dev/null 2>&1; then
    echo "Helm detected — installing kube-prometheus-stack into 'monitoring' namespace (if not present)"
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts || true
    helm repo update || true
    helm upgrade --install monitoring prometheus-community/kube-prometheus-stack -n monitoring --create-namespace -f k3s/prometheus-values.yaml || true
  else
    echo "Helm not found; skipping helm install. Install helm and then run: helm upgrade --install monitoring prometheus-community/kube-prometheus-stack -n monitoring --create-namespace -f k3s/prometheus-values.yaml"
  fi
fi

cat <<'EOF'
Done. Next steps:
  - If helm was not installed and you want Prometheus, install helm and re-run this script.
  - Ensure gateway-admin-token secret contains the actual token value (k3s/prometheus-token.txt) for scraping.
  - For air-gapped deployments, preload images into k3s containerd before applying manifests
EOF

# cleanup temp kubeconfig
if [ -n "${tmp_kubeconfig:-}" ]; then
  rm -f "$tmp_kubeconfig"
fi
