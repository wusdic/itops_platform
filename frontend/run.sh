#!/bin/bash
# ============================================
# Frontend Build/Start Script
# ============================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}ITOps Platform Frontend Setup${NC}"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}Node.js not found! Please install Node.js 18+.${NC}"
    exit 1
fi

echo -e "Node version: $(node --version)"
echo -e "npm version: $(npm --version)"

# Parse command
ACTION=${1:-dev}

case $ACTION in
    install)
        echo -e "${GREEN}Installing dependencies...${NC}"
        npm install
        ;;
    dev)
        echo -e "${GREEN}Starting development server...${NC}"
        npm run dev
        ;;
    build)
        echo -e "${GREEN}Building for production...${NC}"
        npm install
        npm run build
        echo -e "${GREEN}Build complete! Output in dist/${NC}"
        ;;
    *)
        echo "Usage: ./run.sh {install|dev|build}"
        echo "  install - Install dependencies"
        echo "  dev     - Start development server"
        echo "  build   - Build for production"
        ;;
esac