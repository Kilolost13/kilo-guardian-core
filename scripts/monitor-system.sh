#!/bin/bash

################################################################################
# Kilo Guardian Docker System Monitor
#
# A real-time dashboard for monitoring all Docker services
# - Health status with color coding
# - Container uptime
# - CPU and memory usage
# - Auto-refresh every 10 seconds
#
# Usage: ./scripts/monitor-system.sh
# Press Ctrl+C to exit
################################################################################

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
WHITE='\033[1;37m'
GRAY='\033[0;90m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Unicode symbols for better visual
CHECK="✓"
CROSS="✗"
WARN="⚠"
CLOCK="⏱"
MEMORY="💾"
CPU="🔥"
CONTAINER="📦"

# Function to clear screen and move cursor to top
clear_screen() {
    tput clear
    tput cup 0 0
}

# Function to get timestamp
get_timestamp() {
    date "+%Y-%m-%d %H:%M:%S"
}

# Function to get container health status with color
get_health_status() {
    local container=$1
    local health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null)
    local status=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null)

    if [ "$health" = "healthy" ]; then
        echo -e "${GREEN}${CHECK} Healthy${NC}"
    elif [ "$health" = "unhealthy" ]; then
        echo -e "${RED}${CROSS} Unhealthy${NC}"
    elif [ "$health" = "starting" ]; then
        echo -e "${YELLOW}${WARN} Starting${NC}"
    elif [ "$status" = "running" ]; then
        echo -e "${GREEN}${CHECK} Running${NC}"
    elif [ "$status" = "exited" ]; then
        echo -e "${RED}${CROSS} Exited${NC}"
    elif [ "$status" = "restarting" ]; then
        echo -e "${YELLOW}${WARN} Restarting${NC}"
    elif [ "$status" = "paused" ]; then
        echo -e "${YELLOW}${WARN} Paused${NC}"
    else
        echo -e "${GRAY}${WARN} Unknown${NC}"
    fi
}

# Function to get container uptime
get_uptime() {
    local container=$1
    local started=$(docker inspect --format='{{.State.StartedAt}}' "$container" 2>/dev/null)

    if [ -z "$started" ] || [ "$started" = "0001-01-01T00:00:00Z" ]; then
        echo "N/A"
        return
    fi

    # Convert to seconds since epoch
    local started_epoch=$(date -d "$started" +%s 2>/dev/null)
    local now_epoch=$(date +%s)
    local uptime_seconds=$((now_epoch - started_epoch))

    # Format uptime
    local days=$((uptime_seconds / 86400))
    local hours=$(( (uptime_seconds % 86400) / 3600 ))
    local minutes=$(( (uptime_seconds % 3600) / 60 ))

    if [ $days -gt 0 ]; then
        echo "${days}d ${hours}h ${minutes}m"
    elif [ $hours -gt 0 ]; then
        echo "${hours}h ${minutes}m"
    else
        echo "${minutes}m"
    fi
}

# Function to get CPU and memory usage
get_resource_usage() {
    local container=$1
    local stats=$(docker stats --no-stream --format "{{.CPUPerc}}|{{.MemUsage}}|{{.MemPerc}}" "$container" 2>/dev/null)

    if [ -z "$stats" ]; then
        echo "N/A|N/A|N/A"
    else
        echo "$stats"
    fi
}

# Function to display header
display_header() {
    local timestamp=$(get_timestamp)
    echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${CYAN}                    🛡️  KILO GUARDIAN DOCKER MONITOR 🛡️${NC}"
    echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${WHITE}Timestamp: ${CYAN}$timestamp${NC}                          ${GRAY}Press Ctrl+C to exit${NC}"
    echo -e "${BLUE}───────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
}

# Function to display system summary
display_summary() {
    local total=$(docker ps -a --format '{{.Names}}' | wc -l)
    local running=$(docker ps --format '{{.Names}}' | wc -l)
    local healthy=$(docker ps --filter health=healthy --format '{{.Names}}' | wc -l)
    local unhealthy=$(docker ps --filter health=unhealthy --format '{{.Names}}' | wc -l)
    local exited=$(docker ps -a --filter status=exited --format '{{.Names}}' | wc -l)

    echo -e "${BOLD}${WHITE}SYSTEM SUMMARY${NC}"
    echo -e "${BLUE}┌────────────────────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${BLUE}│${NC} Total Containers: ${CYAN}$total${NC}  │  Running: ${GREEN}$running${NC}  │  Healthy: ${GREEN}$healthy${NC}  │  Unhealthy: ${RED}$unhealthy${NC}  │  Exited: ${YELLOW}$exited${NC}  ${BLUE}│${NC}"
    echo -e "${BLUE}└────────────────────────────────────────────────────────────────────────────────┘${NC}"
    echo ""
}

# Function to display service details
display_services() {
    echo -e "${BOLD}${WHITE}SERVICE STATUS${NC}"
    echo -e "${BLUE}┌─────────────────────────────┬──────────────────┬────────────┬──────────┬──────────┬─────────┐${NC}"
    printf "${BLUE}│${NC} ${BOLD}%-27s${NC} ${BLUE}│${NC} ${BOLD}%-16s${NC} ${BLUE}│${NC} ${BOLD}%-10s${NC} ${BLUE}│${NC} ${BOLD}%-8s${NC} ${BLUE}│${NC} ${BOLD}%-8s${NC} ${BLUE}│${NC} ${BOLD}%-7s${NC} ${BLUE}│${NC}\n" \
        "Container Name" "Health Status" "Uptime" "CPU %" "Memory" "Mem %"
    echo -e "${BLUE}├─────────────────────────────┼──────────────────┼────────────┼──────────┼──────────┼─────────┤${NC}"

    # Get list of containers sorted by name
    docker ps -a --format '{{.Names}}' | sort | while read container; do
        local health_status=$(get_health_status "$container")
        local uptime=$(get_uptime "$container")
        local stats=$(get_resource_usage "$container")

        IFS='|' read -r cpu_perc mem_usage mem_perc <<< "$stats"

        # Truncate container name if too long
        local display_name="$container"
        if [ ${#display_name} -gt 27 ]; then
            display_name="${display_name:0:24}..."
        fi

        # Truncate memory usage if too long
        if [ ${#mem_usage} -gt 8 ]; then
            mem_usage="${mem_usage:0:8}"
        fi

        # Color code CPU based on usage
        local cpu_color=$NC
        if [[ "$cpu_perc" =~ ^[0-9]+\.?[0-9]*% ]]; then
            local cpu_num=$(echo "$cpu_perc" | sed 's/%//')
            if (( $(echo "$cpu_num > 80" | bc -l 2>/dev/null || echo 0) )); then
                cpu_color=$RED
            elif (( $(echo "$cpu_num > 50" | bc -l 2>/dev/null || echo 0) )); then
                cpu_color=$YELLOW
            else
                cpu_color=$GREEN
            fi
        fi

        # Color code memory based on usage
        local mem_color=$NC
        if [[ "$mem_perc" =~ ^[0-9]+\.?[0-9]*% ]]; then
            local mem_num=$(echo "$mem_perc" | sed 's/%//')
            if (( $(echo "$mem_num > 80" | bc -l 2>/dev/null || echo 0) )); then
                mem_color=$RED
            elif (( $(echo "$mem_num > 50" | bc -l 2>/dev/null || echo 0) )); then
                mem_color=$YELLOW
            else
                mem_color=$GREEN
            fi
        fi

        printf "${BLUE}│${NC} %-27s ${BLUE}│${NC} %-28s ${BLUE}│${NC} ${CYAN}%-10s${NC} ${BLUE}│${NC} ${cpu_color}%-8s${NC} ${BLUE}│${NC} %-8s ${BLUE}│${NC} ${mem_color}%-7s${NC} ${BLUE}│${NC}\n" \
            "$display_name" "$health_status" "$uptime" "$cpu_perc" "$mem_usage" "$mem_perc"
    done

    echo -e "${BLUE}└─────────────────────────────┴──────────────────┴────────────┴──────────┴──────────┴─────────┘${NC}"
}

# Function to display important services (Kilo-specific)
display_kilo_services() {
    echo ""
    echo -e "${BOLD}${WHITE}KILO GUARDIAN CORE SERVICES${NC}"
    echo -e "${BLUE}┌─────────────────────────────┬──────────────────┬────────────┐${NC}"
    printf "${BLUE}│${NC} ${BOLD}%-27s${NC} ${BLUE}│${NC} ${BOLD}%-16s${NC} ${BLUE}│${NC} ${BOLD}%-10s${NC} ${BLUE}│${NC}\n" \
        "Service" "Status" "Port"
    echo -e "${BLUE}├─────────────────────────────┼──────────────────┼────────────┤${NC}"

    # Define Kilo services with their expected ports
    declare -A kilo_services=(
        ["docker_gateway_1"]="8000"
        ["docker_ai_brain_1"]="9004"
        ["docker_frontend_1"]="3000"
        ["docker_financial_1"]="9005"
        ["docker_reminder_1"]="9002"
        ["docker_meds_1"]="9001"
        ["docker_habits_1"]="9003"
        ["docker_cam_1"]="9007"
        ["docker_library_of_truth_1"]="9006"
        ["docker_ollama_1"]="11434"
    )

    for service in "${!kilo_services[@]}"; do
        local port="${kilo_services[$service]}"
        local health_status=$(get_health_status "$service" 2>/dev/null)

        # Check if container exists
        if ! docker ps -a --format '{{.Names}}' | grep -q "^${service}$"; then
            health_status="${RED}${CROSS} Not Found${NC}"
        fi

        # Shorten service name for display
        local display_name="${service/docker_/}"
        display_name="${display_name/_1/}"
        if [ ${#display_name} -gt 27 ]; then
            display_name="${display_name:0:24}..."
        fi

        printf "${BLUE}│${NC} %-27s ${BLUE}│${NC} %-28s ${BLUE}│${NC} ${CYAN}%-10s${NC} ${BLUE}│${NC}\n" \
            "$display_name" "$health_status" "$port"
    done

    echo -e "${BLUE}└─────────────────────────────┴──────────────────┴────────────┘${NC}"
}

# Function to display footer with helpful commands
display_footer() {
    echo ""
    echo -e "${GRAY}${BLUE}───────────────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "${GRAY}Quick Commands:${NC}"
    echo -e "${GRAY}  • View logs: ${WHITE}docker logs <container_name>${NC}"
    echo -e "${GRAY}  • Restart service: ${WHITE}docker-compose -f infra/docker/docker-compose.yml restart <service>${NC}"
    echo -e "${GRAY}  • Stop monitoring: ${WHITE}Ctrl+C${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════════${NC}"
}

# Main monitoring loop
main() {
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}${CROSS} Error: Docker is not running or you don't have permission to access it.${NC}"
        echo -e "${YELLOW}Try: sudo usermod -aG docker $USER${NC}"
        exit 1
    fi

    # Trap Ctrl+C for clean exit
    trap 'echo -e "\n${CYAN}Monitoring stopped.${NC}"; tput cnorm; exit 0' INT TERM

    # Hide cursor for cleaner display
    tput civis

    while true; do
        # Clear screen and display dashboard
        clear_screen
        display_header
        display_summary
        display_services
        display_kilo_services
        display_footer

        # Wait for 10 seconds before refresh
        sleep 10
    done
}

# Run the main function
main
