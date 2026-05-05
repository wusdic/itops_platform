#!/bin/bash
# ============================================
# ITOps Platform Docker Startup Script
# ============================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  ITOps Platform - Docker Mode${NC}"
echo -e "${BLUE}========================================${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker not found! Please install Docker.${NC}"
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Docker Compose not found!${NC}"
    exit 1
fi

# Parse command
ACTION=${1:-up}

case $ACTION in
    up)
        echo -e "${GREEN}Starting all services...${NC}"
        docker-compose up -d
        echo ""
        echo -e "${GREEN}Services started!${NC}"
        echo "  - API:        http://localhost:8000"
        echo "  - Swagger:    http://localhost:8000/docs"
        echo "  - Frontend:   http://localhost:3000"
        echo "  - PostgreSQL: localhost:5432"
        echo "  - Redis:      localhost:6379"
        echo "  - TDengine:   localhost:6030"
        echo "  - Qdrant:     http://localhost:6333"
        echo "  - MinIO:      http://localhost:9000"
        ;;
    down)
        echo -e "${YELLOW}Stopping all services...${NC}"
        docker-compose down
        ;;
    restart)
        echo -e "${YELLOW}Restarting all services...${NC}"
        docker-compose restart
        ;;
    logs)
        docker-compose logs -f
        ;;
    status)
        docker-compose ps
        ;;
    clean)
        echo -e "${RED}WARNING: This will delete all data!${NC}"
        read -p "Are you sure? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose down -v
            echo -e "${GREEN}All data cleaned!${NC}"
        fi
        ;;
    *)
        echo "Usage: $0 {up|down|restart|logs|status|clean}"
        exit 1
        ;;
esac