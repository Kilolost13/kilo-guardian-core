# Tablet Access to Kilo Guardian

## Quick Start

The easiest way to access Kilo Guardian from your tablet is via SSH tunnel.

### Option 1: One-Time Connection (Simple)

On your tablet terminal, run:

```bash
ssh -L 3000:localhost:30000 -L 8000:localhost:30800 -L 9004:localhost:30904 kilo@192.168.68.66
```

Then open your tablet browser to: **http://localhost:3000**

Keep the SSH terminal open while using Kilo Guardian.

---

### Option 2: Auto-Reconnecting Tunnel (Recommended)

For a persistent connection that survives network drops:

1. **Copy the tunnel script to your tablet:**
   ```bash
   scp kilo@192.168.68.66:~/scripts/start-kilo-tunnel.sh ~/
   chmod +x ~/start-kilo-tunnel.sh
   ```

2. **Edit the script to set your server IP** (if different):
   ```bash
   nano ~/start-kilo-tunnel.sh
   # Change SERVER_IP="192.168.68.66" to your actual IP
   ```

3. **Run the tunnel script:**
   ```bash
   ./start-kilo-tunnel.sh
   ```

4. **Leave the terminal open** and access Kilo Guardian in your browser

---

## Access Points

Once the tunnel is connected:

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:3000 | Main Kilo Guardian UI |
| **Gateway API** | http://localhost:8000 | Backend API Gateway |
| **AI Brain** | http://localhost:9004 | AI Brain Service |

---

## Setup SSH Keys (Optional - No Password Needed)

To avoid typing your password every time:

1. **On your tablet**, generate an SSH key (if you don't have one):
   ```bash
   ssh-keygen -t ed25519
   ```
   Press Enter for all prompts (accept defaults).

2. **Copy your public key to the server:**
   ```bash
   ssh-copy-id kilo@192.168.68.66
   ```
   Enter your password one last time.

3. **Test passwordless login:**
   ```bash
   ssh kilo@192.168.68.66
   ```
   Should connect without asking for a password!

---

## Troubleshooting

### "Connection refused" or "No route to host"
- Verify you're on the same network as the server
- Check server IP: `ping 192.168.68.66`
- Ensure K3s is running: `systemctl status k3s`

### "Address already in use" (port conflict)
- Kill any existing SSH tunnels: `pkill ssh`
- Or use different local ports: `-L 3001:localhost:30000`

### Tunnel keeps disconnecting
- Use the auto-reconnecting script (Option 2)
- Check your WiFi/network stability
- Ensure server is not going to sleep

### Frontend won't load
- Verify tunnel is connected (check terminal)
- Try `curl http://localhost:3000` in tablet terminal
- Check server status: `ssh kilo@192.168.68.66 "~/scripts/k8s-status.sh"`

---

## Server Management from Tablet

Once connected via SSH, you can manage Kilo Guardian:

```bash
# Check system status
~/scripts/k8s-status.sh

# View logs for a service
~/scripts/k8s-logs.sh kilo-gateway

# Restart a service
~/scripts/k8s-restart.sh kilo-meds

# Check all pods
kubectl get pods -n kilo-guardian
```

---

## Network Requirements

- Both tablet and server must be on the same local network
- Server IP: 192.168.68.66
- Required ports: 22 (SSH), 30000 (Frontend), 30800 (Gateway)
- Internet not required (local-only)

---

## Alternative: Direct Access via Ingress (Advanced)

If you configure DNS resolution on your tablet:

Add to `/etc/hosts` (requires root):
```
192.168.68.66  tablet.kilo.local
```

Then access directly: **http://tablet.kilo.local**

---

## Support

For issues or questions:
- Check server logs: `~/scripts/k8s-logs.sh <service-name>`
- View system status: `~/scripts/k8s-status.sh`
- Restart services: `~/scripts/k8s-restart.sh <service-name>`

Last updated: 2026-01-03
