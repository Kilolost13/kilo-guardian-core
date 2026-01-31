# Fully Kiosk Browser Setup Guide
## Kilo AI Memory Assistant - Tablet Kiosk Mode

This guide will help you configure your Android tablet as a dedicated kiosk for the Kilo AI Memory Assistant.

---

## Step 1: Install Fully Kiosk Browser

1. Open **Google Play Store** on your tablet
2. Search for **"Fully Kiosk Browser"**
3. Install the app (free version works great, Plus version has more features)
4. Open Fully Kiosk Browser

---

## Step 2: Initial Setup & Access Settings

1. Open Fully Kiosk Browser
2. Tap the screen **5 times quickly** in the top-right corner
3. Enter default password: **`1234`**
4. You're now in the settings menu

---

## Step 3: Web Content Settings

Navigate to: **Settings → Web Content Settings**

Configure the following:

- **Start URL:** `https://192.168.68.64:3443`
- **Homepage:** `https://192.168.68.64:3443`
- **Reload on connection loss:** ✓ Enable
- **Reload on boot:** ✓ Enable

---

## Step 4: Appearance & Behavior Settings

Navigate to: **Settings → Appearance & Behavior**

Configure:

- **Enable Fullscreen Mode:** ✓ Enable
- **Hide Status Bar:** ✓ Enable
- **Hide Navigation Bar:** ✓ Enable
- **Orientation:** Lock to Portrait (or Landscape if preferred)
- **Keep Screen On:** ✓ Enable
- **Screen Brightness:** Set to comfortable level (60-80%)

---

## Step 5: Advanced Web Settings

Navigate to: **Settings → Advanced Web Settings**

Configure:

- **Ignore SSL Errors:** ✓ Enable (required for self-signed certificate)
- **Enable JavaScript:** ✓ Enable
- **Enable Cookies:** ✓ Enable
- **Enable Local Storage:** ✓ Enable
- **User Agent:** Default (do not change)
- **Clear Cache on Reload:** ✗ Disable
- **Disable Pull-to-Refresh:** ✓ Enable

---

## Step 6: Kiosk Mode Settings

Navigate to: **Settings → Kiosk Mode**

Configure:

- **Enable Kiosk Mode:** ✓ Enable
- **Kiosk Mode Password:** Set a secure password (NOT 1234!)
  - Example: `KiloAI2025` or something you'll remember
  - **IMPORTANT:** Write this password down!
- **Single App Mode:** ✓ Enable
- **Disable Power Button:** ✗ Disable (so you can still turn screen off/on)
- **Exit Kiosk on Power Button:** ✗ Disable

---

## Step 7: Screen Saver & Screensaver Settings

Navigate to: **Settings → Screensaver**

Configure:

- **Enable Screensaver:** ✓ Enable
- **Screensaver Timeout:** 5 minutes (300 seconds)
- **Screensaver Type:** Clock or Daydream
- **Wake on Touch:** ✓ Enable
- **Wake on Motion:** ✓ Enable (if your tablet has motion sensor)

---

## Step 8: Auto-Start Settings

Navigate to: **Settings → Auto-Start**

Configure:

- **Start on Boot:** ✓ Enable
- **Start on Charge:** ✗ Disable (unless you want this)
- **Delay Start (seconds):** 10 seconds
- **Restart App on Crash:** ✓ Enable

---

## Step 9: Remote Admin (Optional but Recommended)

Navigate to: **Settings → Remote Administration**

Configure:

- **Enable Remote Admin:** ✓ Enable (if you want remote access)
- **Remote Admin Password:** Set a password
- **Remote Admin Port:** 2323 (default)

This allows you to access the tablet remotely at:
`http://192.168.68.62:2323` (replace with your tablet IP)

---

## Step 10: Motion Detection (Optional)

Navigate to: **Settings → Motion Detection**

Configure (if you want screen to wake when you approach):

- **Enable Motion Detection:** ✓ Enable
- **Sensitivity:** Medium to High
- **Turn Screen On:** ✓ Enable
- **Take Photo on Motion:** ✗ Disable

---

## Step 11: Device Settings & Permissions

Navigate to: **Settings → Device Admin Settings**

Grant permissions when prompted:

- **Device Administrator:** Allow (for kiosk lock)
- **Accessibility Service:** Allow (for preventing exit)
- **Draw Over Other Apps:** Allow
- **Modify System Settings:** Allow
- **Camera Access:** Allow (for prescription scanning)
- **Storage Access:** Allow

---

## Step 12: Network & Connection

Navigate to: **Settings → Network Settings**

Configure:

- **WiFi SSID:** Your network name
- **Auto-Reconnect on WiFi Loss:** ✓ Enable
- **Show WiFi Status:** ✗ Disable (cleaner look)

---

## Step 13: Final Configuration

1. **Test the URL:**
   - In Fully Kiosk settings, tap "Open Start URL"
   - Verify `https://192.168.68.64:3443` loads correctly
   - Accept any SSL certificate warnings

2. **Set Kiosk Password:**
   - Go to **Settings → Kiosk Mode**
   - Change password from default `1234` to something secure
   - **WRITE IT DOWN!**

3. **Lock the Kiosk:**
   - Tap "Exit Settings" or press Back
   - Enter your new kiosk password
   - The app should now be locked in fullscreen

---

## How to Exit Kiosk Mode

To access settings again:

1. **Tap 5 times** in the top-right corner of the screen
2. Enter your **kiosk password** (the one you set, NOT 1234)
3. You'll be back in settings

---

## Recommended Plus Features (Paid Version - $14.90)

If you purchase Fully Kiosk Browser Plus, you get:

- **No ads**
- **Motion detection** (auto-wake screen)
- **Facial recognition** (security)
- **Task scheduler** (reboot at specific times)
- **Custom JavaScript injection**
- **MQTT support** (home automation)
- **REST API** (advanced remote control)

---

## Troubleshooting

### Screen won't wake from sleep:
- Go to **Settings → Appearance & Behavior**
- Enable "Keep Screen On"
- Or set "Screensaver Timeout" to a longer time

### Can't exit kiosk mode:
- **Force stop method:**
  1. Reboot tablet (hold power button)
  2. Swipe down notification shade QUICKLY before Fully Kiosk starts
  3. Go to Android Settings → Apps → Fully Kiosk Browser
  4. Tap "Force Stop"
  5. You can now access Android normally

### SSL certificate errors:
- Go to **Settings → Advanced Web Settings**
- Make sure "Ignore SSL Errors" is ENABLED

### Page not loading:
- Check WiFi connection
- Verify server is running: `docker-compose ps`
- Test URL in regular Chrome first

### Camera not working for prescription scanning:
- Go to Android Settings → Apps → Fully Kiosk Browser → Permissions
- Grant Camera permission

---

## Auto-Start on Tablet Boot

To make Fully Kiosk start automatically when the tablet powers on:

1. **Settings → Auto-Start → Start on Boot:** ✓ Enable
2. **Android Settings:**
   - Go to Android Settings → Apps → Fully Kiosk Browser
   - Set as default browser (if prompted)
   - Allow "Display over other apps"
   - Disable battery optimization for Fully Kiosk

---

## Optimal Tablet Settings (Android)

For best kiosk experience, configure these Android settings:

1. **Display:**
   - Sleep: Never (or 30 minutes)
   - Brightness: Auto or 60-80%
   - Rotation: Lock to Portrait

2. **Sound:**
   - Volume: 50% or as preferred
   - Do Not Disturb: Off (so notifications work)

3. **Security:**
   - Screen Lock: None (or PIN you'll remember)
   - Allow installation from unknown sources: No (for security)

4. **Developer Options** (Optional):
   - USB Debugging: Disabled (unless you need it)
   - Stay Awake When Charging: Enabled

5. **Battery:**
   - Battery Saver: Off
   - Optimize Fully Kiosk: Off

---

## Quick Reference Card

**URL:** `https://192.168.68.64:3443`

**Exit Kiosk Mode:**
- Tap 5× in top-right corner
- Enter password: `[YOUR PASSWORD HERE]`

**Default Settings Password:** `1234` (change this!)

**Force Exit (Emergency):**
- Reboot tablet
- Quickly swipe down notifications
- Force stop Fully Kiosk Browser app

**Remote Admin URL:** `http://[TABLET_IP]:2323`

---

## Support & More Info

- **Fully Kiosk Website:** https://www.fully-kiosk.com
- **Documentation:** https://www.fully-kiosk.com/en/help
- **Community Forum:** https://forum.fully-kiosk.com

---

**Setup complete! Your tablet is now a dedicated Kilo AI Memory Assistant kiosk!**

Enjoy your hands-free, always-on AI memory assistant! 🧠💊✨
