#!/bin/bash
set -e

# Colors and formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

# Yuga Planner Kubernetes Deployment Script
echo -e "${BOLD}🚀 Yuga Planner - Kubernetes Deployment${RESET}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"

# Check if we're in the correct directory (project root)
if [ ! -f "deploy/kubernetes.yaml" ]; then
    echo -e "${RED}❌ Error: kubernetes.yaml not found${RESET}"
    echo -e "${YELLOW}💡 Please run this script from the project root${RESET}"
    exit 1
fi

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source the credential loading script
echo -e "${BLUE}📋 Loading credential management...${RESET}"
source "${SCRIPT_DIR}/load-credentials.sh"

# Check and load credentials
if ! check_credentials; then
    exit 1
fi

# Check dependencies
echo -e "${BLUE}🔧 Checking dependencies...${RESET}"

if ! command -v envsubst &> /dev/null; then
    echo -e "${RED}❌ Error: envsubst is required but not installed${RESET}"
    echo -e "${YELLOW}💡 Install with: ${CYAN}apt-get install gettext-base${RESET}"
    exit 1
fi

if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ Error: kubectl is required but not installed${RESET}"
    echo -e "${YELLOW}💡 Install from: ${CYAN}https://kubernetes.io/docs/tasks/tools/${RESET}"
    exit 1
fi

echo -e "${GREEN}✅ All dependencies found${RESET}"

# Deploy to Kubernetes
echo -e "${CYAN}🔧 Substituting environment variables and deploying...${RESET}"
envsubst < deploy/kubernetes.yaml | kubectl apply -f -

echo ""
echo -e "${GREEN}✅ Deployment complete!${RESET}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}🌐 Quick Access:${RESET}"
echo -e "  Access URL: ${CYAN}http://<node-ip>:30860${RESET}"
echo ""
echo -e "${BOLD}📊 Useful Commands:${RESET}"
echo -e "  Check status:  ${GREEN}kubectl get pods -l app=yuga-planner${RESET}"
echo -e "  View logs:     ${GREEN}kubectl logs -l app=yuga-planner -f${RESET}"
echo -e "  Get services:  ${GREEN}kubectl get svc -l app=yuga-planner${RESET}"
echo -e "  Port forward:  ${GREEN}kubectl port-forward svc/yuga-planner-service 8080:80${RESET}"
