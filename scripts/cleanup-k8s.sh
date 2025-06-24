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

# Yuga Planner Kubernetes Cleanup Script
echo -e "${BOLD}🧹 Yuga Planner - Kubernetes Cleanup${RESET}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ Error: kubectl is required but not installed${RESET}"
    exit 1
fi

# Check if we're in the correct directory (project root)
if [ ! -f "deploy/kubernetes.yaml" ]; then
    echo -e "${RED}❌ Error: kubernetes.yaml not found${RESET}"
    echo -e "${YELLOW}💡 Please run this script from the project root${RESET}"
    exit 1
fi

# Function to check if resources exist
check_resources() {
    local resource_exists=false

    if kubectl get deployment yuga-planner &> /dev/null; then
        resource_exists=true
    fi

    if kubectl get service yuga-planner-service &> /dev/null; then
        resource_exists=true
    fi

    if kubectl get secret yuga-planner-secrets &> /dev/null; then
        resource_exists=true
    fi

    if kubectl get configmap yuga-planner-config &> /dev/null; then
        resource_exists=true
    fi

    if [ "$resource_exists" = false ]; then
        echo -e "${BLUE}ℹ️  No Yuga Planner resources found in the current namespace${RESET}"
        return 1
    fi

    return 0
}

# Check if any resources exist
echo -e "${BLUE}🔍 Scanning for Yuga Planner resources...${RESET}"
if ! check_resources; then
    echo -e "${GREEN}✅ Nothing to clean up${RESET}"
    exit 0
fi

# Show what will be deleted
echo -e "${YELLOW}📋 Found the following Yuga Planner resources:${RESET}"
kubectl get deployment,service,secret,configmap -l app=yuga-planner 2>/dev/null || true

# Confirm deletion
echo ""
echo -e "${BOLD}⚠️  Warning: This will permanently delete all Yuga Planner resources${RESET}"
read -p "$(echo -e "${YELLOW}❓ Are you sure you want to continue? (y/N): ${RESET}")" -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}❌ Cleanup cancelled${RESET}"
    exit 0
fi

echo -e "${RED}🗑️  Deleting Kubernetes resources...${RESET}"

# Delete resources by label selector (safer approach)
echo -e "  ${CYAN}• Deleting deployment...${RESET}"
kubectl delete deployment -l app=yuga-planner --ignore-not-found=true

echo -e "  ${CYAN}• Deleting service...${RESET}"
kubectl delete service -l app=yuga-planner --ignore-not-found=true

echo -e "  ${CYAN}• Deleting secrets...${RESET}"
kubectl delete secret -l app=yuga-planner --ignore-not-found=true

echo -e "  ${CYAN}• Deleting configmaps...${RESET}"
kubectl delete configmap -l app=yuga-planner --ignore-not-found=true

echo ""
echo -e "${GREEN}✅ Cleanup complete!${RESET}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}🔍 Verification:${RESET}"
echo -e "  Check remaining: ${GREEN}kubectl get all -l app=yuga-planner${RESET}"
