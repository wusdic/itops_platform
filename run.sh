#!/bin/bash
# ============================================
# ITOps Platform Startup Script (Linux/macOS)
# ============================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  ITOps Platform - Starting...${NC}"
echo -e "${BLUE}========================================${NC}"

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${YELLOW}Python Version: $python_version${NC}"

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install --upgrade pip
    pip install -r requirements.txt
fi

# Create necessary directories
mkdir -p logs data reports

# Check configuration
if [ ! -f "config/dev.yaml" ] && [ ! -f "config/prod.yaml" ]; then
    echo -e "${YELLOW}No configuration file found. Using default config/dev.yaml${NC}"
    if [ -f "config/templates/dev.yaml" ]; then
        cp config/templates/dev.yaml config/dev.yaml
        echo -e "${YELLOW}Please edit config/dev.yaml before starting.${NC}"
        exit 0
    fi
fi

# Parse command line arguments
MODE=${1:-dev}
PORT=${2:-8000}

case $MODE in
    dev)
        echo -e "${GREEN}Starting in Development mode on port $PORT${NC}"
        CONFIG_FILE="config/dev.yaml"
        ;;
    prod)
        echo -e "${GREEN}Starting in Production mode on port $PORT${NC}"
        CONFIG_FILE="config/prod.yaml"
        ;;
    *)
        echo -e "${RED}Unknown mode: $MODE${NC}"
        echo "Usage: ./run.sh [dev|prod] [port]"
        exit 1
        ;;
esac

# Export configuration
export CONFIG_FILE=$CONFIG_FILE

# Start the application
echo -e "${GREEN}Starting FastAPI server...${NC}"
python -m uvicorn api.main:app --host 0.0.0.0 --port $PORT --reload