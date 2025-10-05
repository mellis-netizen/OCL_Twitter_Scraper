#!/bin/bash

# ===============================================================================
# Enhanced TGE Monitor System - Deployment Verification Script
# ===============================================================================
# 
# This script verifies that all components of the TGE Monitor system are
# working correctly after deployment
#
# Usage: ./verify-deployment.sh [server-ip]
# ===============================================================================

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[!]${NC} $1"; }

# Test function
test_endpoint() {
    local url="$1"
    local description="$2"
    local expected="$3"
    
    print_status "Testing: $description"
    
    local response=$(curl -s -o /dev/null -w "%{http_code}" "$url" --connect-timeout 10 --max-time 30)
    
    if [ "$response" = "$expected" ]; then
        print_success "$description - HTTP $response"
        return 0
    else
        print_error "$description - HTTP $response (expected $expected)"
        return 1
    fi
}

# Function to test database connection
test_database() {
    print_status "Testing database connection..."
    
    if command -v psql >/dev/null 2>&1; then
        if sudo -u postgres psql -c "SELECT 1;" >/dev/null 2>&1; then
            print_success "PostgreSQL is running and accessible"
        else
            print_error "PostgreSQL connection failed"
            return 1
        fi
    else
        print_warning "psql not available for testing"
    fi
}

# Function to test Redis connection
test_redis() {
    print_status "Testing Redis connection..."
    
    if command -v redis-cli >/dev/null 2>&1; then
        if redis-cli ping >/dev/null 2>&1; then
            print_success "Redis is running and accessible"
        else
            print_error "Redis connection failed"
            return 1
        fi
    else
        print_warning "redis-cli not available for testing"
    fi
}

# Function to test services
test_services() {
    print_status "Testing system services..."
    
    local services=("tge-monitor-api" "tge-monitor-worker" "postgresql" "redis" "nginx")
    local all_services_ok=true
    
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service"; then
            print_success "$service is running"
        else
            print_error "$service is not running"
            all_services_ok=false
        fi
    done
    
    if [ "$all_services_ok" = true ]; then
        return 0
    else
        return 1
    fi
}

# Function to test application logs
test_logs() {
    print_status "Checking application logs for errors..."
    
    local log_dir="/opt/tge-monitor/logs"
    local has_errors=false
    
    if [ -d "$log_dir" ]; then
        # Check for recent errors in logs
        local recent_errors=$(find "$log_dir" -name "*.log" -mtime -1 -exec grep -l -i "error\|critical\|fatal" {} \; 2>/dev/null || true)
        
        if [ -n "$recent_errors" ]; then
            print_warning "Recent errors found in logs:"
            echo "$recent_errors"
            has_errors=true
        else
            print_success "No recent errors in application logs"
        fi
    else
        print_warning "Log directory not found: $log_dir"
    fi
    
    return 0
}

# Function to test API functionality
test_api_functionality() {
    local server_ip="$1"
    
    print_status "Testing API functionality..."
    
    # Test health endpoint
    local health_response=$(curl -s "http://${server_ip}/health" --connect-timeout 10 --max-time 30)
    
    if echo "$health_response" | grep -q "healthy\|ok"; then
        print_success "Health endpoint responding correctly"
    else
        print_error "Health endpoint not responding correctly"
        echo "Response: $health_response"
        return 1
    fi
    
    # Test API docs endpoint
    if test_endpoint "http://${server_ip}/docs" "API Documentation" "200"; then
        print_success "API documentation is accessible"
    else
        print_warning "API documentation endpoint may have issues"
    fi
    
    return 0
}

# Function to run comprehensive verification
run_comprehensive_verification() {
    local server_ip="$1"
    local is_local="$2"
    
    echo "==============================================================================="
    echo "          Enhanced TGE Monitor System - Deployment Verification"
    echo "==============================================================================="
    echo ""
    
    local tests_passed=0
    local tests_total=0
    
    # Test 1: Services (local only)
    if [ "$is_local" = "true" ]; then
        tests_total=$((tests_total + 1))
        if test_services; then
            tests_passed=$((tests_passed + 1))
        fi
        
        # Test 2: Database (local only)
        tests_total=$((tests_total + 1))
        if test_database; then
            tests_passed=$((tests_passed + 1))
        fi
        
        # Test 3: Redis (local only)
        tests_total=$((tests_total + 1))
        if test_redis; then
            tests_passed=$((tests_passed + 1))
        fi
        
        # Test 4: Logs (local only)
        tests_total=$((tests_total + 1))
        if test_logs; then
            tests_passed=$((tests_passed + 1))
        fi
    fi
    
    # Test 5: API endpoints (can be remote)
    if [ -n "$server_ip" ]; then
        tests_total=$((tests_total + 1))
        if test_api_functionality "$server_ip"; then
            tests_passed=$((tests_passed + 1))
        fi
        
        # Test individual endpoints
        local endpoints=(
            "http://${server_ip}/health:Health Check:200"
            "http://${server_ip}/docs:API Documentation:200"
        )
        
        for endpoint_info in "${endpoints[@]}"; do
            IFS=':' read -r url description expected <<< "$endpoint_info"
            tests_total=$((tests_total + 1))
            if test_endpoint "$url" "$description" "$expected"; then
                tests_passed=$((tests_passed + 1))
            fi
        done
    fi
    
    echo ""
    echo "==============================================================================="
    echo "                            VERIFICATION SUMMARY"
    echo "==============================================================================="
    echo ""
    
    if [ $tests_passed -eq $tests_total ]; then
        print_success "All tests passed! ($tests_passed/$tests_total)"
        echo ""
        echo "🎉 Your TGE Monitor System is fully operational!"
        echo ""
        
        if [ -n "$server_ip" ]; then
            echo "🌐 Access URLs:"
            echo "   • API Documentation: http://${server_ip}/docs"
            echo "   • Health Check:      http://${server_ip}/health"
            echo "   • WebSocket:         ws://${server_ip}/ws"
            echo ""
        fi
        
        echo "📋 Next Steps:"
        echo "   1. Configure email settings in /opt/tge-monitor/.env"
        echo "   2. Add Twitter API credentials (optional)"
        echo "   3. Setup SSL certificate with Let's Encrypt"
        echo "   4. Configure monitoring alerts"
        echo "   5. Setup regular backups"
        echo ""
        
        return 0
    else
        print_error "Some tests failed ($tests_passed/$tests_total passed)"
        echo ""
        echo "🔧 Troubleshooting:"
        echo "   • Check service status: sudo systemctl status tge-monitor-*"
        echo "   • View logs: tail -f /opt/tge-monitor/logs/*.log"
        echo "   • Check configuration: cat /opt/tge-monitor/.env"
        echo "   • Run health check: /opt/tge-monitor/health_check.sh"
        echo ""
        
        return 1
    fi
}

# Main function
main() {
    local server_ip="$1"
    local is_local="false"
    
    # Determine if we're running locally on the server
    if [ -z "$server_ip" ]; then
        # Check if we're on the server itself
        if [ -d "/opt/tge-monitor" ]; then
            is_local="true"
            server_ip="localhost"
            print_status "Running local verification on the server"
        else
            print_error "Usage: $0 [server-ip]"
            print_error "If running on the server, no IP needed"
            print_error "If running remotely, provide the server IP"
            exit 1
        fi
    else
        print_status "Running remote verification against $server_ip"
    fi
    
    run_comprehensive_verification "$server_ip" "$is_local"
}

main "$@"