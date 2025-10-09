#!/bin/bash
# Health check script for TGE Swarm All-in-One container
# Cost Optimization Engineer: Claude

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    local status=$1
    local message=$2
    
    if [ "$status" = "OK" ]; then
        echo -e "${GREEN}✓${NC} $message"
    elif [ "$status" = "WARNING" ]; then
        echo -e "${YELLOW}⚠${NC} $message"
    else
        echo -e "${RED}✗${NC} $message"
    fi
}

# Function to check if service is running
check_service() {
    local service_name=$1
    local port=$2
    local path=${3:-"/health"}
    
    if curl -f --connect-timeout 5 "http://localhost:$port$path" >/dev/null 2>&1; then
        print_status "OK" "$service_name is healthy (port $port)"
        return 0
    else
        print_status "ERROR" "$service_name is not responding (port $port)"
        return 1
    fi
}

# Function to check process
check_process() {
    local process_name=$1
    
    if pgrep -f "$process_name" >/dev/null; then
        print_status "OK" "Process '$process_name' is running"
        return 0
    else
        print_status "ERROR" "Process '$process_name' is not running"
        return 1
    fi
}

# Function to check memory usage
check_memory() {
    local memory_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
    local memory_usage_int=${memory_usage%.*}
    
    if [ "$memory_usage_int" -lt 85 ]; then
        print_status "OK" "Memory usage: ${memory_usage}%"
        return 0
    elif [ "$memory_usage_int" -lt 95 ]; then
        print_status "WARNING" "Memory usage: ${memory_usage}%"
        return 0
    else
        print_status "ERROR" "Memory usage critically high: ${memory_usage}%"
        return 1
    fi
}

# Function to check disk space
check_disk() {
    local disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    
    if [ "$disk_usage" -lt 80 ]; then
        print_status "OK" "Disk usage: ${disk_usage}%"
        return 0
    elif [ "$disk_usage" -lt 90 ]; then
        print_status "WARNING" "Disk usage: ${disk_usage}%"
        return 0
    else
        print_status "ERROR" "Disk usage critically high: ${disk_usage}%"
        return 1
    fi
}

# Function to check load average
check_load() {
    local load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    local load_int=${load_avg%.*}
    local cpu_cores=$(nproc)
    
    if [ "$load_int" -lt "$cpu_cores" ]; then
        print_status "OK" "Load average: $load_avg (cores: $cpu_cores)"
        return 0
    elif [ "$load_int" -lt $((cpu_cores * 2)) ]; then
        print_status "WARNING" "Load average: $load_avg (cores: $cpu_cores)"
        return 0
    else
        print_status "ERROR" "Load average critically high: $load_avg (cores: $cpu_cores)"
        return 1
    fi
}

echo "TGE Swarm Health Check - $(date)"
echo "================================"

# Initialize error counter
errors=0

# Check core TGE Swarm services
echo "Checking TGE Swarm Services:"
check_service "TGE Queen API" 8080 "/health" || ((errors++))
check_service "Metrics Endpoint" 8001 "/metrics" || ((errors++))
check_service "Memory Coordinator" 8002 "/health" || ((errors++))

echo ""
echo "Checking System Resources:"
check_memory || ((errors++))
check_disk || ((errors++))
check_load || ((errors++))

echo ""
echo "Checking Processes:"
check_process "python.*queen" || ((errors++))
check_process "python.*coordinator" || ((errors++))
check_process "python.*agent" || ((errors++))

echo ""
echo "Checking Logs for Errors:"
# Check for recent errors in logs
recent_errors=$(find /app/logs -name "*.log" -mtime -1 -exec grep -i "error\|exception\|critical" {} \; 2>/dev/null | wc -l)
if [ "$recent_errors" -eq 0 ]; then
    print_status "OK" "No recent errors in logs"
elif [ "$recent_errors" -lt 10 ]; then
    print_status "WARNING" "$recent_errors recent errors found in logs"
else
    print_status "ERROR" "$recent_errors recent errors found in logs"
    ((errors++))
fi

echo ""
echo "Checking Database Connectivity:"
if command -v pg_isready >/dev/null 2>&1; then
    if pg_isready -h postgres -p 5432 -U swarm_user >/dev/null 2>&1; then
        print_status "OK" "PostgreSQL is accessible"
    else
        print_status "ERROR" "PostgreSQL is not accessible"
        ((errors++))
    fi
else
    print_status "WARNING" "pg_isready not available, skipping PostgreSQL check"
fi

echo ""
echo "Checking Redis Connectivity:"
if command -v redis-cli >/dev/null 2>&1; then
    if redis-cli -h redis -p 6379 ping >/dev/null 2>&1; then
        print_status "OK" "Redis is accessible"
    else
        print_status "ERROR" "Redis is not accessible"
        ((errors++))
    fi
else
    print_status "WARNING" "redis-cli not available, skipping Redis check"
fi

echo ""
echo "================================"
if [ "$errors" -eq 0 ]; then
    print_status "OK" "All health checks passed!"
    exit 0
elif [ "$errors" -lt 3 ]; then
    print_status "WARNING" "$errors issues found - system degraded but functional"
    exit 1
else
    print_status "ERROR" "$errors critical issues found - system unhealthy"
    exit 2
fi