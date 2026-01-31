#!/bin/bash
# Kilo Mission Control Wrapper with Resource Guard
cd /home/brain_ai/Desktop/AI_stuff/old_hacksaw_fingers

# Check available memory (require at least 1GB for Kilo)
mem_avail=$(free -g | grep Mem | awk '{print $7}')
if [ "$mem_avail" -lt 1 ]; then
    echo "ERROR: Not enough memory to start Kilo. Available: ${mem_avail}GB"
    exit 1
fi

echo "Starting Kilo Mission Control V3 (Unified Command Center)..."

# Try V3 first (integrated chat), fallback to V2
if [ -f "kilo_mission_control_v3.py" ]; then
    echo "→ Launching V3 with integrated AI chat & memory"
    ./venv/bin/python3 kilo_mission_control_v3.py
elif [ -f "kilo_mission_control_v2.py" ]; then
    echo "→ Launching V2 (fallback)"
    ./venv/bin/python3 kilo_mission_control_v2.py
else
    echo "ERROR: Mission Control not found!"
    exit 1
fi