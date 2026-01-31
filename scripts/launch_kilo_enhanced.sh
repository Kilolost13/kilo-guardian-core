#!/bin/bash
# Launch Kilo Agent ENHANCED UI - The Best Version!

cd ~/projects/kilo/core/

echo "🧹 Clearing Python cache..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null

echo ""
echo "🚀 Launching KILO AGENT - ENHANCED EDITION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✨ NEW FEATURES:"
echo "  ✓ Cluster Status View - See REAL deployments & pods"
echo "  ✓ Manual Control Panel - Help Kilo when brain fails"
echo "  ✓ Proposed Actions - Kilo's AI suggestions"
echo "  ✓ Everything in ONE window"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Force Python to not use cached bytecode
PYTHONDONTWRITEBYTECODE=1 python3 -u kilo_agent_ui_enhanced.py
