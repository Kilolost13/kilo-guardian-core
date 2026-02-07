# Kilo K3S Parts

Kubernetes manifests and configuration files for deploying Kilo Guardian services on K3s.

See the main [README.md](../README.md) for architecture overview.

## Contents

This directory contains deployment scripts, verification tools, and guides for managing the Kilo Guardian system on K3s (Kubernetes).

### Deployment Scripts

- **`start-kilo-system.sh`** - Main script to start all Kilo Guardian services on K3s
- **`rebuild-meds.sh`** - Rebuild and redeploy the medication management service
- **`build-socketio.sh`** - Build the SocketIO relay service
- **`import-images-to-k3s.sh`** - Import Docker images into K3s local registry
- **`fix-image-pull-policy.sh`** - Fix ImagePullPolicy settings for K3s deployments

### Verification & Testing

- **`verify-system.sh`** - Verify that all Kilo Guardian services are running correctly
- **`test-all-endpoints.sh`** - Test all service API endpoints
- **`test-frontend-endpoints.sh`** - Test frontend and gateway endpoints

### Configuration & Setup

- **`setup-kubectl-alias.sh`** - Set up kubectl aliases for easier cluster management
- **`remove-docker.sh`** - Clean up Docker installations

### Documentation

- **`BROWSER_ACCESS_GUIDE.md`** - Guide for accessing services via web browser
- **`TABLET_INTEGRATION_GUIDE.md`** - Guide for integrating tablets with the system
- **`FRONTEND_STATUS_REPORT.md`** - Status report on frontend deployment
- **`SYSTEM_FIXED_REPORT.md`** - System fixes and improvements report
- **`CLEAN_SYSTEM_REPORT.md`** - Clean system deployment report

### Other Files

- **`port list for 192.168.68.64`** - Port mappings for the Kilo server

## Deployment

The Kilo Guardian system uses K3s (lightweight Kubernetes) for orchestration. Services are deployed in the `kilo-guardian` namespace with NodePort access for external connectivity.

### Quick Start

1. Ensure K3s is installed and running
2. Run `./start-kilo-system.sh` to deploy all services
3. Run `./verify-system.sh` to check deployment status
4. Run `./test-all-endpoints.sh` to validate API endpoints

### Architecture

All microservices communicate via REST APIs and are accessible through:
- **Internal ClusterIP**: For service-to-service communication
- **NodePort**: For external access from tablets and other devices
- **Gateway Service**: Unified API gateway on port 30000

For more details, see the main repository README and individual service documentation.
