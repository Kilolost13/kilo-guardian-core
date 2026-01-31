# 🛡️ Kilo Guardian System Monitor

A real-time dashboard for monitoring all Docker services in the Kilo AI Memory Assistant.

## Features

✅ **Real-time monitoring** - Updates every 10 seconds
✅ **Health status tracking** - Visual indicators for each service
✅ **Color-coded display** - Green (healthy), Yellow (starting), Red (unhealthy/stopped)
✅ **Container uptime** - Shows how long each service has been running
✅ **Resource usage** - CPU and memory consumption per container
✅ **System summary** - Quick overview of total/running/healthy containers
✅ **Kilo-specific services** - Dedicated section for core Guardian services
✅ **Clean dashboard** - Auto-refreshing display with Unicode symbols

## Usage

### Start Monitoring

```bash
./scripts/monitor-system.sh
```

### Stop Monitoring

Press `Ctrl+C` to exit cleanly.

## Dashboard Layout

```
═══════════════════════════════════════════════════════════════════════════════════
                    🛡️  KILO GUARDIAN DOCKER MONITOR 🛡️
═══════════════════════════════════════════════════════════════════════════════════
Timestamp: 2025-12-26 10:30:45                          Press Ctrl+C to exit
───────────────────────────────────────────────────────────────────────────────────

SYSTEM SUMMARY
┌────────────────────────────────────────────────────────────────────────────────┐
│ Total Containers: 13  │  Running: 9  │  Healthy: 8  │  Unhealthy: 1  │  Exited: 4  │
└────────────────────────────────────────────────────────────────────────────────┘

SERVICE STATUS
┌─────────────────────────────┬──────────────────┬────────────┬──────────┬──────────┬─────────┐
│ Container Name              │ Health Status    │ Uptime     │ CPU %    │ Memory   │ Mem %   │
├─────────────────────────────┼──────────────────┼────────────┼──────────┼──────────┼─────────┤
│ docker_ai_brain_1           │ ✓ Healthy        │ 2h 15m     │ 5.23%    │ 512MB    │ 3.2%    │
│ docker_gateway_1            │ ✓ Healthy        │ 3h 45m     │ 1.05%    │ 128MB    │ 0.8%    │
│ ...                         │ ...              │ ...        │ ...      │ ...      │ ...     │
└─────────────────────────────┴──────────────────┴────────────┴──────────┴──────────┴─────────┘

KILO GUARDIAN CORE SERVICES
┌─────────────────────────────┬──────────────────┬────────────┐
│ Service                     │ Status           │ Port       │
├─────────────────────────────┼──────────────────┼────────────┤
│ gateway                     │ ✓ Healthy        │ 8000       │
│ ai_brain                    │ ✓ Healthy        │ 9004       │
│ frontend                    │ ✗ Exited         │ 3000       │
│ ...                         │ ...              │ ...        │
└─────────────────────────────┴──────────────────┴────────────┘
```

## Color Codes

- 🟢 **Green** - Healthy, running normally
- 🟡 **Yellow** - Starting, restarting, or moderate resource usage
- 🔴 **Red** - Unhealthy, exited, or high resource usage
- ⚪ **Gray** - Unknown status or N/A

## Status Indicators

- ✓ **Healthy** - Container is running and passing health checks
- ✓ **Running** - Container is running (no health check configured)
- ⚠ **Starting** - Container is starting up
- ⚠ **Restarting** - Container is restarting
- ✗ **Unhealthy** - Container failed health checks
- ✗ **Exited** - Container has stopped

## Resource Usage Alerts

**CPU Usage:**
- Green: 0-50%
- Yellow: 50-80%
- Red: 80-100%

**Memory Usage:**
- Green: 0-50%
- Yellow: 50-80%
- Red: 80-100%

## Quick Commands (from Dashboard)

### View Container Logs
```bash
docker logs <container_name>
docker logs <container_name> --tail 50 --follow
```

### Restart a Service
```bash
docker-compose -f infra/docker/docker-compose.yml restart <service_name>
```

### Stop a Service
```bash
docker-compose -f infra/docker/docker-compose.yml stop <service_name>
```

### Start All Services
```bash
LIBRARY_ADMIN_KEY=test123 docker-compose -f infra/docker/docker-compose.yml up -d
```

## Troubleshooting

### Permission Denied
If you get "permission denied" errors:
```bash
# Add your user to docker group
sudo usermod -aG docker $USER

# Log out and log back in, or run:
newgrp docker
```

### Docker Not Running
```bash
# Start Docker service
sudo systemctl start docker

# Enable Docker to start on boot
sudo systemctl enable docker
```

### Script Not Executable
```bash
chmod +x scripts/monitor-system.sh
```

## Dependencies

- **Docker** - Container runtime
- **bash** - Shell interpreter (built-in on Linux)
- **bc** - Basic calculator for CPU/memory calculations (usually pre-installed)
- **tput** - Terminal control (usually pre-installed)

## Advanced Usage

### Custom Refresh Interval

Edit the script and change the `sleep` value at the end:

```bash
# Change from 10 seconds to 5 seconds
sleep 5
```

### Monitor Specific Containers Only

You can filter the output by modifying the `docker ps` commands in the script.

### Export Statistics

Redirect output to a file for logging:

```bash
./scripts/monitor-system.sh > monitor.log 2>&1
```

## Notes

- The dashboard updates every 10 seconds by default
- Cursor is hidden during monitoring for cleaner display
- Pressing `Ctrl+C` will cleanly exit and restore the cursor
- Resource statistics may show "N/A" for stopped containers
- First update may take a few seconds as Docker stats are gathered

## Integration with Other Tools

### Use with tmux/screen

Perfect for running in a terminal multiplexer:

```bash
# In tmux
tmux new-session -s monitor './scripts/monitor-system.sh'

# Detach: Ctrl+B, then D
# Reattach: tmux attach -t monitor
```

### Use with watch (alternative)

If you prefer `watch`:

```bash
watch -n 10 -c 'docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
```

## Support

For issues or feature requests, see the main project documentation in `/docs`.

---

**Made with ❤️ for the Kilo Guardian Project**
