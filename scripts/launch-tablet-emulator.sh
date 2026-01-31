#!/bin/bash

# Tablet Emulator Launcher
# Opens Chrome in a tablet-sized window with touch emulation

KIOSK_URL="https://192.168.68.64:3443"

# Tablet resolutions to choose from:
# iPad Pro 12.9": 1024x1366
# iPad: 768x1024
# Android Tablet: 800x1280
# Large Tablet: 1024x768 (landscape)

WIDTH=800
HEIGHT=1280

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

echo "Launching Tablet Emulator..."
echo "Browser: $BROWSER"
echo "Resolution: ${WIDTH}x${HEIGHT}"
echo "URL: $KIOSK_URL"

# Launch Chrome in app mode with tablet emulation
$BROWSER \
  --app="$KIOSK_URL" \
  --window-size=$WIDTH,$HEIGHT \
  --user-agent="Mozilla/5.0 (Linux; Android 10; Tablet) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Safari/537.36" \
  --touch-events=enabled \
  --enable-features=OverlayScrollbar \
  --force-device-scale-factor=1.0 \
  --ignore-certificate-errors \
  --disable-pinch \
  --overscroll-history-navigation=0 \
  --no-first-run \
  --no-default-browser-check \
  &

echo ""
echo "Tablet emulator launched!"
echo "Window size: ${WIDTH}x${HEIGHT} (portrait mode)"
echo ""
echo "To test different sizes, edit this script and change WIDTH/HEIGHT"
echo "Common tablet sizes:"
echo "  - iPad: WIDTH=768 HEIGHT=1024"
echo "  - iPad Pro: WIDTH=1024 HEIGHT=1366"
echo "  - Android Tablet: WIDTH=800 HEIGHT=1280"
echo "  - Landscape mode: Swap WIDTH and HEIGHT values"
