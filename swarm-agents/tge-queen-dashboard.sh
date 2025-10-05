#!/bin/bash

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                TGE QUEEN SWARM DASHBOARD                       ║"
echo "║          Real-time Monitoring & Control Interface             ║"
echo "╚════════════════════════════════════════════════════════════════╝"

# Function to display swarm status
show_swarm_status() {
    echo ""
    echo "🔄 SWARM STATUS"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if [[ -f "./logs/queen-orchestration.log" ]]; then
        echo "👑 Queen: $(tail -1 ./logs/queen-orchestration.log | grep -o 'PHASE [0-9]*' | tail -1 || echo 'INITIALIZING')"
    else
        echo "👑 Queen: STANDBY"
    fi
    
    if [[ -f "./logs/worker-progress.log" ]]; then
        echo "👥 Workers Active: $(grep -c 'WORKER.*ACTIVE' ./logs/worker-progress.log 2>/dev/null || echo '0')"
        echo "✅ Tasks Completed: $(grep -c 'TASK.*COMPLETED' ./logs/worker-progress.log 2>/dev/null || echo '0')"
        echo "⚠️  Issues Found: $(grep -c 'ISSUE.*DETECTED' ./logs/worker-progress.log 2>/dev/null || echo '0')"
    else
        echo "👥 Workers: STANDBY"
    fi
    
    echo "🧠 Memory: $([ -d './safla-memory' ] && echo 'INITIALIZED' || echo 'NOT INITIALIZED')"
    echo "📊 Reports: $(ls -1 ./reports/*.md 2>/dev/null | wc -l | tr -d ' ') files"
}

# Function to show recent activity
show_recent_activity() {
    echo ""
    echo "📝 RECENT ACTIVITY (Last 10 events)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Combine and sort logs by timestamp
    if [[ -f "./logs/queen-orchestration.log" ]] || [[ -f "./logs/worker-progress.log" ]]; then
        {
            [[ -f "./logs/queen-orchestration.log" ]] && tail -5 "./logs/queen-orchestration.log" | sed 's/^/👑 /'
            [[ -f "./logs/worker-progress.log" ]] && tail -5 "./logs/worker-progress.log" | sed 's/^/👥 /'
        } | tail -10
    else
        echo "No activity logs found. Run './tge-queen-orchestrator.sh' to start."
    fi
}

# Function to show performance metrics
show_performance_metrics() {
    echo ""
    echo "⚡ PERFORMANCE METRICS"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if [[ -f "./.claude-flow/metrics/performance.json" ]]; then
        echo "📊 Analysis Speed: $(jq -r '.analysis_speed // "N/A"' ./.claude-flow/metrics/performance.json)"
        echo "🎯 Accuracy Score: $(jq -r '.accuracy_score // "N/A"' ./.claude-flow/metrics/performance.json)"
        echo "💾 Memory Usage: $(jq -r '.memory_usage // "N/A"' ./.claude-flow/metrics/performance.json)"
        echo "🔄 Tasks/Hour: $(jq -r '.tasks_per_hour // "N/A"' ./.claude-flow/metrics/performance.json)"
    else
        echo "No performance metrics available yet."
    fi
}

# Function to show key findings summary
show_key_findings() {
    echo ""
    echo "🔍 KEY FINDINGS SUMMARY"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if [[ -f "./reports/EXECUTIVE_SUMMARY.md" ]]; then
        echo "📋 Executive Summary Available:"
        head -10 "./reports/EXECUTIVE_SUMMARY.md" | tail -8
        echo "..."
        echo "📄 Full report: ./reports/EXECUTIVE_SUMMARY.md"
    elif [[ -f "./reports/queen-initial-analysis.md" ]]; then
        echo "📋 Initial Analysis Complete:"
        head -5 "./reports/queen-initial-analysis.md" | tail -3
        echo "📄 Full report: ./reports/queen-initial-analysis.md"
    else
        echo "No analysis reports available yet."
        echo "Run './tge-queen-orchestrator.sh' to begin analysis."
    fi
}

# Function to show available commands
show_commands() {
    echo ""
    echo "🎮 AVAILABLE COMMANDS"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  start     - Start Queen Orchestrator"
    echo "  stop      - Stop all swarm activities"
    echo "  status    - Show detailed status"
    echo "  logs      - View live logs"
    echo "  reports   - List all generated reports"
    echo "  reset     - Reset swarm state"
    echo "  help      - Show this help"
    echo ""
    echo "Usage: $0 [command]"
}

# Function to handle commands
handle_command() {
    case "$1" in
        "start")
            echo "🚀 Starting Queen Orchestrator..."
            ./tge-queen-orchestrator.sh
            ;;
        "stop")
            echo "🛑 Stopping swarm activities..."
            pkill -f "claude-flow"
            echo "✅ All swarm processes stopped."
            ;;
        "status")
            show_swarm_status
            show_performance_metrics
            ;;
        "logs")
            echo "📊 Live Logs (Press Ctrl+C to exit):"
            tail -f ./logs/*.log 2>/dev/null || echo "No log files found."
            ;;
        "reports")
            echo "📊 Generated Reports:"
            ls -la ./reports/*.md 2>/dev/null | awk '{print "  " $9 " (" $5 " bytes, " $6 " " $7 ")"}'
            ;;
        "reset")
            echo "🔄 Resetting swarm state..."
            rm -rf ./safla-memory ./logs ./reports
            mkdir -p ./logs ./reports
            echo "✅ Swarm state reset complete."
            ;;
        "help")
            show_commands
            ;;
        *)
            # Default dashboard view
            clear
            echo "╔════════════════════════════════════════════════════════════════╗"
            echo "║                TGE QUEEN SWARM DASHBOARD                       ║"
            echo "║          Real-time Monitoring & Control Interface             ║"
            echo "╚════════════════════════════════════════════════════════════════╝"
            
            show_swarm_status
            show_recent_activity
            show_key_findings
            show_commands
            ;;
    esac
}

# Create necessary directories
mkdir -p ./logs ./reports

# Handle command line arguments
if [[ $# -eq 0 ]]; then
    # Interactive dashboard mode
    while true; do
        handle_command ""
        echo ""
        echo "Press Enter to refresh, or type a command:"
        read -t 5 input
        if [[ -n "$input" ]]; then
            handle_command "$input"
        fi
        clear
    done
else
    # Single command mode
    handle_command "$1"
fi