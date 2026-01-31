#!/bin/bash
# Launch Kilo Agent with FRESH imports (no cache)

cd ~/projects/kilo/core/

echo "🧹 Clearing Python cache..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null

echo "🚀 Launching Kilo Agent with fresh imports..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "This is the REAL Kilo - not a chatbot!"
echo ""
echo "Capabilities:"
echo "  ✓ Proactive monitoring of k3s cluster"
echo "  ✓ Proposes actions with reasoning"
echo "  ✓ Executes with your approval"
echo "  ✓ Uses LLM brain for intelligent decisions"
echo "  ✓ Learns patterns and earns autonomy"
echo ""
echo "Starting agent UI..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Force Python to not use cached bytecode
PYTHONDONTWRITEBYTECODE=1 python3 -u kilo_agent_ui.py
