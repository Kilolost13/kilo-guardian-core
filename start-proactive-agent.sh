#!/bin/bash
# Start Kilo Proactive Agent on HP Server
# This script runs the agent with direct ClusterIP access

# Get ClusterIPs from K3s
REMINDER_IP=$(sudo kubectl get svc -n kilo-guardian kilo-reminder -o jsonpath='{.spec.clusterIP}')
FINANCIAL_IP=$(sudo kubectl get svc -n kilo-guardian kilo-financial -o jsonpath='{.spec.clusterIP}')
HABITS_IP=$(sudo kubectl get svc -n kilo-guardian kilo-habits -o jsonpath='{.spec.clusterIP}')
MEDS_IP=$(sudo kubectl get svc -n kilo-guardian kilo-meds -o jsonpath='{.spec.clusterIP}')
AI_BRAIN_IP=$(sudo kubectl get svc -n kilo-guardian kilo-ai-brain -o jsonpath='{.spec.clusterIP}')

echo "🔧 Service ClusterIPs:"
echo "  Reminder: $REMINDER_IP:9002"
echo "  Financial: $FINANCIAL_IP:9005"
echo "  Habits: $HABITS_IP:9000"
echo "  Meds: $MEDS_IP:9001"
echo "  AI Brain: $AI_BRAIN_IP:9004"
echo

# Set environment variables for the agent
export REMINDER_URL="http://$REMINDER_IP:9002"
export FINANCIAL_URL="http://$FINANCIAL_IP:9005"
export HABITS_URL="http://$HABITS_IP:9000"
export MEDS_URL="http://$MEDS_IP:9001"
export AI_BRAIN_URL="http://localhost:9200"  # Agent API service

# Change to repo root directory to ensure shared package can be imported
cd ~/kilo-guardian-core

# Run the agent
python3 kilo_proactive_agent.py "$@"
