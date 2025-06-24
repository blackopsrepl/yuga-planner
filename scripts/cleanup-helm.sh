#!/bin/bash
set -e

# Colors and formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
RESET='\033[0m'

# Yuga Planner Helm Cleanup Script
echo -e "${BOLD}🧹 Yuga Planner - Helm Cleanup${RESET}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"

# Check if helm is available
if ! command -v helm &> /dev/null; then
    echo -e "${RED}❌ Error: helm is required but not installed${RESET}"
    echo -e "${YELLOW}💡 Install from: ${CYAN}https://helm.sh/docs/intro/install/${RESET}"
    exit 1
fi

# Configuration (same defaults as deploy script)
RELEASE_NAME="${HELM_RELEASE_NAME:-yuga-planner}"
# Get current namespace, fallback to default if not set
CURRENT_NAMESPACE=$(kubectl config view --minify --output 'jsonpath={..namespace}' 2>/dev/null || echo "default")
NAMESPACE="${HELM_NAMESPACE:-$CURRENT_NAMESPACE}"

echo -e "${BOLD}📦 Configuration:${RESET}"
echo -e "  Release:   ${MAGENTA}$RELEASE_NAME${RESET}"
echo -e "  Namespace: ${MAGENTA}$NAMESPACE${RESET}"

# Check if the release exists
echo ""
echo -e "${BLUE}🔍 Scanning for Helm release...${RESET}"
if ! helm list -n "$NAMESPACE" | grep -q "^$RELEASE_NAME"; then
    echo -e "${BLUE}ℹ️  Helm release '${MAGENTA}$RELEASE_NAME${BLUE}' not found in namespace '${MAGENTA}$NAMESPACE${BLUE}'${RESET}"
    echo -e "${GREEN}✅ Nothing to clean up${RESET}"
    exit 0
fi

# Show release information
echo -e "${YELLOW}📋 Found Helm release:${RESET}"
helm list -n "$NAMESPACE" | grep "^$RELEASE_NAME" || true

echo ""
echo -e "${BLUE}📊 Release details:${RESET}"
helm status "$RELEASE_NAME" -n "$NAMESPACE" --no-hooks || true

# Confirm deletion
echo ""
echo -e "${BOLD}⚠️  Warning: This will permanently uninstall the Helm release${RESET}"
read -p "$(echo -e "${YELLOW}❓ Are you sure you want to uninstall '${MAGENTA}$RELEASE_NAME${YELLOW}'? (y/N): ${RESET}")" -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}❌ Cleanup cancelled${RESET}"
    exit 0
fi

echo -e "${RED}🗑️  Uninstalling Helm release...${RESET}"
helm uninstall "$RELEASE_NAME" -n "$NAMESPACE"

echo -e "${GREEN}✅ Helm release uninstalled successfully!${RESET}"

# Check if namespace should be cleaned up (optional)
if [ "$NAMESPACE" != "default" ]; then
    echo ""
    echo -e "${YELLOW}🤔 The namespace '${MAGENTA}$NAMESPACE${YELLOW}' still exists${RESET}"
    read -p "$(echo -e "${YELLOW}❓ Do you want to delete the namespace as well? (y/N): ${RESET}")" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Check if namespace has other resources
        OTHER_RESOURCES=$(kubectl get all -n "$NAMESPACE" --ignore-not-found=true 2>/dev/null | grep -v "^NAME" | wc -l)
        if [ "$OTHER_RESOURCES" -gt 0 ]; then
            echo -e "${YELLOW}⚠️  Warning: Namespace '${MAGENTA}$NAMESPACE${YELLOW}' contains other resources${RESET}"
            kubectl get all -n "$NAMESPACE" 2>/dev/null || true
            read -p "$(echo -e "${RED}❓ Are you sure you want to delete the entire namespace? (y/N): ${RESET}")" -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                kubectl delete namespace "$NAMESPACE"
                echo -e "${GREEN}✅ Namespace '${MAGENTA}$NAMESPACE${GREEN}' deleted${RESET}"
            else
                echo -e "${BLUE}ℹ️  Namespace '${MAGENTA}$NAMESPACE${BLUE}' preserved${RESET}"
            fi
        else
            kubectl delete namespace "$NAMESPACE"
            echo -e "${GREEN}✅ Empty namespace '${MAGENTA}$NAMESPACE${GREEN}' deleted${RESET}"
        fi
    else
        echo -e "${BLUE}ℹ️  Namespace '${MAGENTA}$NAMESPACE${BLUE}' preserved${RESET}"
    fi
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}🔍 Verification Commands:${RESET}"
echo -e "  List releases:      ${GREEN}helm list -A${RESET}"
echo -e "  Check resources:    ${GREEN}kubectl get all -l app.kubernetes.io/instance=$RELEASE_NAME -A${RESET}"
