#!/bin/bash
# Launch Kilo Agent - FRESH START (no cache!)

cd ~/projects/kilo/core/

echo "🧹 AGGRESSIVELY CLEARING ALL PYTHON CACHE..."
# Kill any running instances
pkill -9 -f kilo_agent_ui 2>/dev/null

# Delete ALL cache files recursively
find ~/projects/kilo -type f -name "*.pyc" -delete 2>/dev/null
find ~/projects/kilo -type f -name "*.pyo" -delete 2>/dev/null
find ~/projects/kilo -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Also clean current directory specifically
rm -rf ./__pycache__ 2>/dev/null
rm -f ./*.pyc 2>/dev/null

echo ""
echo "🚀 LAUNCHING KILO - COMPLETE EDITION (FRESH CODE)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✨ FEATURES:"
echo "  ✓ HP Connection Status - Green/Red indicator with reconnect"
echo "  ✓ Kilo Activity Banner - See what Kilo is doing"
echo "  ✓ Running Pod Count - Real-time pod statistics"
echo "  ✓ IMPROVED CHAT - Understands natural language!"
echo ""
echo "💬 CHAT EXAMPLES:"
echo "  - 'hey what's running?'"
echo "  - 'any proposals?'"
echo "  - 'scale frontend to 5'"
echo "  - 'help'"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Force fresh imports - DISABLE ALL CACHING
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

# Run with -B flag to not write bytecode
python3 -B -u kilo_agent_ui_complete.py
