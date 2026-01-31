#!/bin/bash

################################################################################
# Kilo Guardian Quick Status Check
#
# One-time snapshot of Docker system status (no auto-refresh)
# Use this for quick checks without the full monitoring dashboard
#
# Usage: ./scripts/check-status.sh
################################################################################

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
GRAY='\033[0;90m'
BOLD='\033[1m'
NC='\033[0m'

# Symbols
CHECK="✓"
CROSS="✗"
WARN="⚠"

echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${CYAN}          🛡️  KILO GUARDIAN STATUS SNAPSHOT 🛡️${NC}"
echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${WHITE}Timestamp: ${CYAN}$(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo ""

# Count containers
total=$(docker ps -a --format '{{.Names}}' | wc -l)
running=$(docker ps --format '{{.Names}}' | wc -l)
healthy=$(docker ps --filter health=healthy --format '{{.Names}}' | wc -l)
unhealthy=$(docker ps --filter health=unhealthy --format '{{.Names}}' | wc -l)
exited=$(docker ps -a --filter status=exited --format '{{.Names}}' | wc -l)

echo -e "${BOLD}${WHITE}SUMMARY${NC}"
echo -e "  Total Containers: ${CYAN}$total${NC}"
echo -e "  Running: ${GREEN}$running${NC}"
echo -e "  Healthy: ${GREEN}$healthy${NC}"
echo -e "  Unhealthy: ${RED}$unhealthy${NC}"
echo -e "  Exited: ${YELLOW}$exited${NC}"
echo ""

echo -e "${BOLD}${WHITE}CORE SERVICES${NC}"
echo ""

# Check core services
declare -A services=(
    ["docker_gateway_1"]="Gateway (API Router)"
    ["docker_ai_brain_1"]="AI Brain (RAG/Chat)"
    ["docker_ollama_1"]="Ollama (LLM)"
    ["docker_frontend_1"]="Frontend (React UI)"
    ["docker_financial_1"]="Financial Service"
    ["docker_reminder_1"]="Reminder Service"
    ["docker_meds_1"]="Medications"
    ["docker_habits_1"]="Habits Tracker"
    ["docker_cam_1"]="Camera Monitor"
    ["docker_library_of_truth_1"]="Library of Truth"
)

for container in "${!services[@]}"; do
    desc="${services[$container]}"

    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null)
        if [ "$health" = "healthy" ]; then
            status="${GREEN}${CHECK} Running (Healthy)${NC}"
        elif [ "$health" = "unhealthy" ]; then
            status="${RED}${CROSS} Running (Unhealthy)${NC}"
        else
            status="${GREEN}${CHECK} Running${NC}"
        fi
    elif docker ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
        status="${RED}${CROSS} Stopped${NC}"
    else
        status="${GRAY}${WARN} Not Found${NC}"
    fi

    printf "  %-25s %s\n" "$desc" "$status"
done

echo ""
echo -e "${BOLD}${WHITE}QUICK ACTIONS${NC}"
echo -e "  • Monitor live: ${CYAN}./scripts/monitor-system.sh${NC}"
echo -e "  • View logs: ${CYAN}docker logs <container_name>${NC}"
echo -e "  • Restart all: ${CYAN}docker-compose -f infra/docker/docker-compose.yml restart${NC}"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
