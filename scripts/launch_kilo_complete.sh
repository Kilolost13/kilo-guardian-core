#!/bin/bash
# Launch Kilo Agent - COMPLETE EDITION
# The final version with EVERYTHING!

cd ~/projects/kilo/core/

echo "🧹 Clearing Python cache..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
find . -name "*.pyo" -delete 2>/dev/null
rm -rf ./__pycache__ 2>/dev/null

echo ""
echo "🚀 LAUNCHING KILO - COMPLETE EDITION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✨ COMPLETE FEATURES:"
echo "  ✓ Cluster Status View - See what's actually there"
echo "  ✓ Proposed Actions - Kilo's AI suggestions with reasoning"
echo "  ✓ Manual Controls - Override when Kilo's being dumb"
echo "  ✓ CHAT INTERFACE - Talk to Kilo! Yell at him! Give commands!"
echo ""
echo "💬 TRY SAYING:"
echo "  - 'scale frontend to 5'"
echo "  - 'Why did you propose that?'"
echo "  - 'You silly goose!'"
echo "  - 'Good job!'"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Force fresh imports
PYTHONDONTWRITEBYTECODE=1 python3 -u kilo_agent_ui_complete.py
