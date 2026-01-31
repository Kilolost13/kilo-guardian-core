#!/usr/bin/env bash
set -euo pipefail

# Kilo Guardian - K3s Installation Script
# This script installs K3s and configures kubectl access

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "========================================="
echo "🚀 Kilo Guardian - K3s Installation"
echo "========================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}❌ Please run this script as a regular user, not root${NC}"
    echo "The script will prompt for sudo when needed"
    exit 1
fi

# Check if K3s is already installed
if command -v k3s &> /dev/null; then
    echo -e "${YELLOW}⚠️  K3s is already installed!${NC}"
    echo ""
    k3s --version
    echo ""
    read -p "Do you want to reinstall K3s? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping K3s installation..."
        SKIP_INSTALL=true
    else
        echo "Uninstalling existing K3s..."
        if [ -f /usr/local/bin/k3s-uninstall.sh ]; then
            sudo /usr/local/bin/k3s-uninstall.sh
        fi
        SKIP_INSTALL=false
    fi
else
    SKIP_INSTALL=false
fi

if [ "$SKIP_INSTALL" = false ]; then
    echo "========================================="
    echo "📦 Step 1: Installing K3s"
    echo "========================================="
    echo ""
    echo "This will take 2-3 minutes..."
    echo ""

    # Install K3s
    if curl -sfL https://get.k3s.io | sh -; then
        echo ""
        echo -e "${GREEN}✅ K3s installed successfully!${NC}"
    else
        echo ""
        echo -e "${RED}❌ K3s installation failed${NC}"
        exit 1
    fi

    echo ""
    echo "Waiting for K3s to start..."
    sleep 5
fi

# Check if K3s is running
echo "========================================="
echo "🔍 Checking K3s Status"
echo "========================================="
echo ""

if sudo systemctl is-active --quiet k3s; then
    echo -e "${GREEN}✅ K3s service is running${NC}"
    sudo systemctl status k3s --no-pager | head -10
else
    echo -e "${YELLOW}⚠️  K3s service not running, attempting to start...${NC}"
    sudo systemctl start k3s
    sleep 5

    if sudo systemctl is-active --quiet k3s; then
        echo -e "${GREEN}✅ K3s service started${NC}"
    else
        echo -e "${RED}❌ Failed to start K3s service${NC}"
        echo "Check logs: sudo journalctl -u k3s -f"
        exit 1
    fi
fi

echo ""
echo "========================================="
echo "🔧 Step 2: Configuring kubectl Access"
echo "========================================="
echo ""

# Create .kube directory
echo "Creating ~/.kube directory..."
mkdir -p ~/.kube

# Backup existing config if it exists
if [ -f ~/.kube/config ]; then
    echo "Backing up existing kubectl config..."
    cp ~/.kube/config ~/.kube/config.backup.$(date +%Y%m%d-%H%M%S)
fi

# Copy K3s config
echo "Copying K3s config..."
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config

# Fix ownership
echo "Setting ownership..."
sudo chown $USER:$USER ~/.kube/config

# Fix permissions
echo "Setting permissions..."
chmod 600 ~/.kube/config

echo -e "${GREEN}✅ kubectl configured${NC}"
echo ""

echo "========================================="
echo "✅ Step 3: Verifying Installation"
echo "========================================="
echo ""

# Test kubectl
echo "Testing kubectl access..."
if kubectl version --short 2>/dev/null; then
    echo -e "${GREEN}✅ kubectl is working!${NC}"
else
    echo -e "${RED}❌ kubectl not working${NC}"
    exit 1
fi

echo ""
echo "Checking cluster nodes..."
kubectl get nodes

echo ""
echo "Checking system pods..."
kubectl get pods -A

echo ""
echo "========================================="
echo "🎉 K3s Installation Complete!"
echo "========================================="
echo ""
echo -e "${GREEN}✅ K3s is installed and running${NC}"
echo -e "${GREEN}✅ kubectl is configured${NC}"
echo -e "${GREEN}✅ Cluster is ready${NC}"
echo ""
echo "========================================="
echo "📊 Cluster Information"
echo "========================================="
echo ""

# Show cluster info
kubectl cluster-info

echo ""
echo "========================================="
echo "🚀 Next Steps"
echo "========================================="
echo ""
echo "1. Verify MCP server connection:"
echo "   claude mcp list"
echo ""
echo "2. Build and deploy Kilo Guardian:"
echo "   cd /home/brain_ai/Desktop/AI_stuff/old_hacksaw_fingers"
echo "   ./deploy-to-k3s.sh"
echo ""
echo "3. Check deployment status:"
echo "   kubectl get pods -n kilo-guardian"
echo ""
echo "========================================="
echo "📖 Useful Commands"
echo "========================================="
echo ""
echo "  View nodes:           kubectl get nodes"
echo "  View all pods:        kubectl get pods -A"
echo "  K3s status:           sudo systemctl status k3s"
echo "  K3s logs:             sudo journalctl -u k3s -f"
echo "  Restart K3s:          sudo systemctl restart k3s"
echo ""
echo "Full documentation: K3S_SETUP_GUIDE.md"
echo ""
