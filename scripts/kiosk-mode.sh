#!/bin/bash

# Kiosk Mode Launcher for Kilo AI Memory Assistant
# This script launches Chrome/Chromium in kiosk mode for tablet use

# Configuration
KIOSK_URL="https://192.168.68.64:3443"

# Detect which browser is available
if command -v google-chrome &> /dev/null; then
    BROWSER="google-chrome"
elif command -v chromium-browser &> /dev/null; then
    BROWSER="chromium-browser"
elif command -v chromium &> /dev/null; then
    BROWSER="chromium"
else
    echo "Error: Chrome/Chromium not found. Please install Chrome or Chromium."
    exit 1
fi

echo "Launching Kilo AI in kiosk mode..."
echo "Browser: $BROWSER"
echo "URL: $KIOSK_URL"

# Launch browser in kiosk mode with tablet-optimized flags
$BROWSER \
  --kiosk \
  --start-fullscreen \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-translate \
  --disable-features=TranslateUI \
  --ignore-certificate-errors \
  --disable-pinch \
  --overscroll-history-navigation=0 \
  --disable-cache \
  --disk-cache-size=1 \
  --no-first-run \
  --no-default-browser-check \
  --touch-events=enabled \
  "$KIOSK_URL" &

echo "Kiosk mode launched! Press Ctrl+Alt+F4 or Alt+F4 to exit."
