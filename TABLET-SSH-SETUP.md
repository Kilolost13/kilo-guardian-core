# Tablet SSH Setup Guide

**Goal:** Access your HP server from your tablet to interact with Kilo agent

---

## Step 1: Install SSH Client on Tablet

### For Android Tablets

**Option A: Termux (Recommended)**
1. Install **Termux** from F-Droid or Google Play
2. Open Termux
3. Update packages:
   ```bash
   pkg update && pkg upgrade
   pkg install openssh
   ```

**Option B: JuiceSSH**
1. Install **JuiceSSH** from Google Play
2. Easier UI, less powerful than Termux

**Option C: ConnectBot**
1. Install **ConnectBot** from Google Play
2. Simple, lightweight

### For iPad/iOS Tablets

**Option A: Termius (Best UI)**
1. Install **Termius** from App Store
2. Free for basic SSH

**Option B: Blink Shell**
1. Install **Blink Shell** from App Store
2. More powerful, terminal emulator

---

## Step 2: Connect to HP Server

### From Termux (Android)

```bash
ssh kilo@192.168.68.56
```

**First time connecting:**
- You'll see: "The authenticity of host... can't be established"
- Type: `yes`
- Enter password when prompted

### From JuiceSSH (Android)

1. Tap **Connections** → **+**
2. Enter:
   - **Nickname:** HP Server
   - **Type:** SSH
   - **Address:** 192.168.68.56
   - **Port:** 22
   - **Identity:** Create new
     - **Username:** kilo
     - **Password:** [your password]
3. Tap **Save**
4. Tap connection to connect

### From Termius (iOS)

1. Tap **+** → **New Host**
2. Enter:
   - **Alias:** HP Server
   - **Hostname:** 192.168.68.56
   - **Username:** kilo
   - **Password:** [your password]
3. Tap **Save**
4. Tap connection to connect

---

## Step 3: Set Up SSH Keys (Optional but Recommended)

**Why?** No password needed, more secure

### On Tablet (Termux or Blink)

```bash
# Generate SSH key
ssh-keygen -t ed25519 -C "tablet"

# Press Enter for all prompts (accept defaults)

# Copy public key to HP server
ssh-copy-id kilo@192.168.68.56
# Enter password one last time
```

Now you can connect without password:
```bash
ssh kilo@192.168.68.56
```

---

## Step 4: Quick Commands for Tablet

### Check Kilo Agent Status
```bash
ssh kilo@192.168.68.56 'curl -s http://localhost:9200/agent/status | jq .'
```

### See Recent Agent Messages
```bash
ssh kilo@192.168.68.56 'curl -s http://localhost:9200/agent/messages | jq .'
```

### Run Agent Once (Manual Check)
```bash
ssh kilo@192.168.68.56 '~/start-proactive-agent.sh once'
```

### Check K3s Pods
```bash
ssh kilo@192.168.68.56 'sudo kubectl get pods -n kilo-guardian'
```

### View Agent API Logs
```bash
ssh kilo@192.168.68.56 'sudo journalctl -u kilo-agent-api -f'
```

---

## Step 5: Access Dashboard from Tablet

The dashboard is already accessible from your tablet browser!

### Access URL

**Direct Frontend Access:**
```
http://192.168.68.56:30002
```

**Or via Gateway:**
```
http://192.168.68.56:30801
```

### What You Can Do

On your tablet dashboard:
1. **See proactive notifications** from Kilo agent
   - Reminders about medications
   - Budget warnings
   - Habit reminders
   - Spending insights

2. **Send commands to Kilo:**
   - "show my reminders"
   - "what's my spending today"
   - "show my habits"
   - "list medications"

3. **Regular AI chat**
   - Ask questions
   - Get help
   - Upload images (if camera works)

---

## Step 6: Create Shortcuts (Optional)

### Termux Shortcuts (Android)

Create file: `~/.shortcuts/kilo-status.sh`
```bash
#!/data/data/com.termux/files/usr/bin/bash
ssh kilo@192.168.68.56 '~/start-proactive-agent.sh once'
```

Make executable:
```bash
chmod +x ~/.shortcuts/kilo-status.sh
```

Now you can run from Termux widget!

### iOS Shortcuts (iPad)

1. Open **Shortcuts** app
2. Create **New Shortcut**
3. Add action: **Run Script Over SSH**
4. Configure:
   - Host: 192.168.68.56
   - User: kilo
   - Script: `~/start-proactive-agent.sh once`
5. Save as "Check Kilo"

Add to home screen for one-tap access!

---

## Troubleshooting

### Can't Connect

**Check if HP is reachable:**
```bash
ping 192.168.68.56
```

**Check if SSH is running on HP:**
```bash
# From another computer
ssh kilo@192.168.68.56
```

**Make sure you're on same network:**
- Tablet and HP must be on same WiFi (192.168.68.x)

### Connection Timeout

**If HP server is asleep, wake it:**
```bash
# From Beelink
ssh kilo@192.168.68.56
```

Or use Wake-on-LAN if configured.

### Permission Denied

**Wrong password?**
- Try from Beelink first: `ssh kilo@192.168.68.56`
- Confirm password works
- Then try from tablet

**SSH keys not working?**
```bash
# Check permissions on HP
ls -la ~/.ssh/authorized_keys
# Should be: -rw------- (600)

# Fix if needed:
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

---

## Security Tips

### 1. Use SSH Keys Instead of Passwords
More secure and convenient.

### 2. Change Default SSH Port (Optional)
Edit `/etc/ssh/sshd_config` on HP:
```
Port 2222  # Change from 22
```

Then connect:
```bash
ssh -p 2222 kilo@192.168.68.56
```

### 3. Disable Password Login (After SSH Keys Work)
Edit `/etc/ssh/sshd_config`:
```
PasswordAuthentication no
```

### 4. Use Firewall Rules
Only allow SSH from local network:
```bash
sudo ufw allow from 192.168.68.0/24 to any port 22
```

---

## Quick Reference

### Connect to HP
```bash
ssh kilo@192.168.68.56
```

### Dashboard URL
```
http://192.168.68.56:30002
```

### Agent API
```
http://192.168.68.56:9200
```

### Check Agent
```bash
ssh kilo@192.168.68.56 '~/start-proactive-agent.sh once'
```

### View Agent Messages
```bash
curl http://192.168.68.56:9200/agent/messages
```

---

## What You Can Do Now

### From Tablet Browser
✅ Open dashboard at `http://192.168.68.56:30002`
✅ See Kilo's proactive notifications in chat
✅ Send commands: "show spending", "show reminders"
✅ Upload images, use voice input
✅ View all your data visualizations

### From Tablet SSH
✅ Run agent manually
✅ Check service status
✅ View logs
✅ Manage K3s pods
✅ Access all server functions

---

**You now have full Kilo access from your tablet!** 🎉

Both through the web dashboard AND SSH terminal access.

---

Back to [[AGENT-CHAT-INTEGRATION|Agent Integration Guide]]
