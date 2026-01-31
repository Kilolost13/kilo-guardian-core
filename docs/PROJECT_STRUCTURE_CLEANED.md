# Kilo AI Microservice Project Structure (Cleaned)

Your project is now organized as follows:

- `/frontend/kilo-react-frontend/` — Main React frontend (with Dockerfile)
- `/services/` — All backend microservices (each with its own Dockerfile)
- `/k3s/` — All Kubernetes manifests (YAMLs) for deploying the system
- `/Kilo_K3S_parts/` — Utility scripts and troubleshooting tools for k3s
- `/docs/` — Documentation and guides
- `/artifacts/` — Build/test artifacts
- `/shared/` — Shared code/models

## How to Deploy/Run

1. **Build Docker images** for each service and the frontend (requires Docker or nerdctl)
2. **Push images to a registry** (if not building directly on the k3s node)
3. **Apply manifests** from `/k3s/` using `kubectl apply -f <manifest>.yaml`
4. **Use scripts** in `/Kilo_K3S_parts/` for troubleshooting and automation

---

**Next:** I will create a simple launcher script and desktop icon for you.
