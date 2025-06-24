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

# Yuga Planner Helm Deployment Script
echo -e "${BOLD}⎈ Yuga Planner - Helm Deployment${RESET}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"

# Check if we're in the correct directory (project root)
if [ ! -d "deploy/helm" ] && [ ! -f "deploy/helm/Chart.yaml" ]; then
    echo -e "${RED}❌ Error: Helm chart not found${RESET}"
    echo -e "${YELLOW}💡 Please ensure deploy/helm/Chart.yaml exists${RESET}"
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

if ! command -v helm &> /dev/null; then
    echo -e "${RED}❌ Error: helm is required but not installed${RESET}"
    echo -e "${YELLOW}💡 Install from: ${CYAN}https://helm.sh/docs/intro/install/${RESET}"
    exit 1
fi

if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ Error: kubectl is required but not installed${RESET}"
    echo -e "${YELLOW}💡 Install from: ${CYAN}https://kubernetes.io/docs/tasks/tools/${RESET}"
    exit 1
fi

echo -e "${GREEN}✅ All dependencies found${RESET}"

# Configuration
RELEASE_NAME="${HELM_RELEASE_NAME:-yuga-planner}"
CURRENT_NAMESPACE=$(kubectl config view --minify --output 'jsonpath={..namespace}' 2>/dev/null || echo "default")
NAMESPACE="${HELM_NAMESPACE:-$CURRENT_NAMESPACE}"
CHART_PATH="${HELM_CHART_PATH:-deploy/helm}"

echo ""
echo -e "${BOLD}📦 Deployment Configuration:${RESET}"
echo -e "  Release:   ${MAGENTA}$RELEASE_NAME${RESET}"
echo -e "  Namespace: ${MAGENTA}$NAMESPACE${RESET}"
echo -e "  Chart:     ${MAGENTA}$CHART_PATH${RESET}"

# Create namespace if it doesn't exist
if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
    echo -e "${CYAN}🏗️ Creating namespace: ${MAGENTA}$NAMESPACE${RESET}"
    kubectl create namespace "$NAMESPACE"
fi

# Prepare Helm values with environment variables
echo -e "${BLUE}🔧 Preparing deployment values...${RESET}"
HELM_VALUES=""
HELM_VALUES="$HELM_VALUES --set secrets.nebiusApiKey=$NEBIUS_API_KEY"
HELM_VALUES="$HELM_VALUES --set secrets.nebiusModel=$NEBIUS_MODEL"
HELM_VALUES="$HELM_VALUES --set secrets.modalTokenId=$MODAL_TOKEN_ID"
HELM_VALUES="$HELM_VALUES --set secrets.modalTokenSecret=$MODAL_TOKEN_SECRET"
HELM_VALUES="$HELM_VALUES --set secrets.hfModel=$HF_MODEL"
HELM_VALUES="$HELM_VALUES --set secrets.hfToken=$HF_TOKEN"

# Add optional environment variables if set
if [ ! -z "$IMAGE_TAG" ]; then
    HELM_VALUES="$HELM_VALUES --set image.tag=$IMAGE_TAG"
    echo -e "  Using custom image tag: ${YELLOW}$IMAGE_TAG${RESET}"
fi

if [ ! -z "$REPLICAS" ]; then
    HELM_VALUES="$HELM_VALUES --set deployment.replicas=$REPLICAS"
    echo -e "  Using custom replica count: ${YELLOW}$REPLICAS${RESET}"
fi

# Deploy with Helm
echo ""
if helm list -n "$NAMESPACE" | grep -q "^$RELEASE_NAME"; then
    echo -e "${CYAN}🔄 Upgrading existing Helm release...${RESET}"
    helm upgrade "$RELEASE_NAME" "$CHART_PATH" \
        --namespace "$NAMESPACE" \
        $HELM_VALUES \
        --timeout 300s \
        --wait
else
    echo -e "${CYAN}🆕 Installing new Helm release...${RESET}"
    helm install "$RELEASE_NAME" "$CHART_PATH" \
        --namespace "$NAMESPACE" \
        $HELM_VALUES \
        --timeout 300s \
        --wait
fi

echo ""
echo -e "${GREEN}✅ Deployment complete!${RESET}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"

echo -e "${BOLD}📊 Release Information:${RESET}"
helm status "$RELEASE_NAME" -n "$NAMESPACE" --no-hooks

echo ""
echo -e "${BOLD}🔍 Useful Commands:${RESET}"
echo -e "  Check pods:    ${GREEN}kubectl get pods -l app.kubernetes.io/instance=$RELEASE_NAME -n $NAMESPACE${RESET}"
echo -e "  View logs:     ${GREEN}kubectl logs -l app.kubernetes.io/instance=$RELEASE_NAME -n $NAMESPACE -f${RESET}"
echo -e "  Port forward:  ${GREEN}kubectl port-forward svc/$RELEASE_NAME 8080:80 -n $NAMESPACE${RESET}"
echo -e "  Uninstall:     ${RED}helm uninstall $RELEASE_NAME -n $NAMESPACE${RESET}"
