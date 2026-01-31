#!/bin/bash
# Launch the REAL Kilo - Autonomous Agent with Tools

cd ~/projects/kilo/core/

echo "🚀 Launching Kilo Autonomous Agent..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "This is the REAL Kilo - not a chatbot!"
echo ""
echo "Capabilities:"
echo "  ✓ Proactive monitoring of k3s cluster"
echo "  ✓ Proposes actions with reasoning"
echo "  ✓ Executes with your approval"
echo "  ✓ Can modify code, kubectl resources, files"
echo "  ✓ Learns patterns and earns autonomy"
echo ""
echo "Starting agent UI..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if venv exists
if [ -d "../venv" ]; then
    source ../venv/bin/activate
    python3 kilo_agent_ui.py
else
    python3 kilo_agent_ui.py
fi
