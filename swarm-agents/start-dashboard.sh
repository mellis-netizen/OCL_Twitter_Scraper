#!/bin/bash

# TGE Swarm Dashboard Startup Script
# Starts the React dashboard for monitoring the TGE Swarm Optimization System

set -e

DASHBOARD_DIR="$(dirname "$0")/dashboard"
DEFAULT_PORT=3000
PORT=${1:-$DEFAULT_PORT}

echo "🚀 Starting TGE Swarm Dashboard..."
echo "📁 Dashboard directory: $DASHBOARD_DIR"
echo "🌐 Port: $PORT"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16+ to continue."
    echo "📥 Download from: https://nodejs.org/"
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 16 ]; then
    echo "❌ Node.js version 16+ is required. Current version: $(node --version)"
    echo "📥 Please upgrade Node.js from: https://nodejs.org/"
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install npm to continue."
    exit 1
fi

# Navigate to dashboard directory
if [ ! -d "$DASHBOARD_DIR" ]; then
    echo "❌ Dashboard directory not found: $DASHBOARD_DIR"
    exit 1
fi

cd "$DASHBOARD_DIR"

# Check if package.json exists
if [ ! -f "package.json" ]; then
    echo "❌ package.json not found in dashboard directory"
    exit 1
fi

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies"
        exit 1
    fi
    echo "✅ Dependencies installed successfully"
else
    echo "✅ Dependencies already installed"
fi

# Check if environment file exists
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "⚠️  Please review and update .env file with your configuration"
fi

# Start the development server
echo "🎯 Starting dashboard server on port $PORT..."
echo "🔗 Dashboard will be available at: http://localhost:$PORT"
echo "📊 Monitoring TGE Swarm Optimization System"
echo ""
echo "⏹️  Press Ctrl+C to stop the dashboard"
echo ""

# Set port and start
export PORT=$PORT
npm start

# Cleanup message
echo ""
echo "👋 TGE Swarm Dashboard stopped"