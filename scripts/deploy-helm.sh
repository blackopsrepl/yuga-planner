#!/bin/bash
set -e

# Yuga Planner Helm Deployment Script
# This script loads credentials from environment variables or creds.py and deploys using Helm

echo "🚀 Deploying Yuga Planner using Helm..."

# Check if we're in the correct directory (project root)
if [ ! -d "deploy/helm" ] && [ ! -f "deploy/helm/Chart.yaml" ]; then
    echo "❌ Error: Helm chart not found. Please ensure deploy/helm/Chart.yaml exists."
    exit 1
fi

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source the credential loading script
source "${SCRIPT_DIR}/load-credentials.sh"

# Check and load credentials
if ! check_credentials; then
    exit 1
fi

# Check if helm is available
if ! command -v helm &> /dev/null; then
    echo "❌ Error: helm is required but not installed."
    echo "💡 Install Helm from: https://helm.sh/docs/intro/install/"
    exit 1
fi

# Configuration
RELEASE_NAME="${HELM_RELEASE_NAME:-yuga-planner}"
# Get current namespace, fallback to default if not set
CURRENT_NAMESPACE=$(kubectl config view --minify --output 'jsonpath={..namespace}' 2>/dev/null || echo "default")
NAMESPACE="${HELM_NAMESPACE:-$CURRENT_NAMESPACE}"
CHART_PATH="${HELM_CHART_PATH:-deploy/helm}"

echo "📦 Helm Release: $RELEASE_NAME"
echo "🏷️  Namespace: $NAMESPACE"
echo "📂 Chart Path: $CHART_PATH"

# Create namespace if it doesn't exist
if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
    echo "🏗️  Creating namespace: $NAMESPACE"
    kubectl create namespace "$NAMESPACE"
fi

# Prepare Helm values with environment variables
HELM_VALUES=""
HELM_VALUES="$HELM_VALUES --set env.NEBIUS_API_KEY=$NEBIUS_API_KEY"
HELM_VALUES="$HELM_VALUES --set env.NEBIUS_MODEL=$NEBIUS_MODEL"
HELM_VALUES="$HELM_VALUES --set env.MODAL_TOKEN_ID=$MODAL_TOKEN_ID"
HELM_VALUES="$HELM_VALUES --set env.MODAL_TOKEN_SECRET=$MODAL_TOKEN_SECRET"
HELM_VALUES="$HELM_VALUES --set env.HF_MODEL=$HF_MODEL"
HELM_VALUES="$HELM_VALUES --set env.HF_TOKEN=$HF_TOKEN"

# Add optional environment variables if set
if [ ! -z "$IMAGE_TAG" ]; then
    HELM_VALUES="$HELM_VALUES --set image.tag=$IMAGE_TAG"
fi

if [ ! -z "$REPLICAS" ]; then
    HELM_VALUES="$HELM_VALUES --set replicaCount=$REPLICAS"
fi

# Check if release already exists
if helm list -n "$NAMESPACE" | grep -q "^$RELEASE_NAME"; then
    echo "🔄 Upgrading existing Helm release..."
    helm upgrade "$RELEASE_NAME" "$CHART_PATH" \
        --namespace "$NAMESPACE" \
        $HELM_VALUES \
        --timeout 300s \
        --wait
else
    echo "🆕 Installing new Helm release..."
    helm install "$RELEASE_NAME" "$CHART_PATH" \
        --namespace "$NAMESPACE" \
        $HELM_VALUES \
        --timeout 300s \
        --wait
fi

echo "✅ Deployment complete!"
echo ""
echo "📊 Release Information:"
helm status "$RELEASE_NAME" -n "$NAMESPACE"
echo ""
echo "🔍 Useful commands:"
echo "  • Check pods: kubectl get pods -l app.kubernetes.io/instance=$RELEASE_NAME -n $NAMESPACE"
echo "  • View logs: kubectl logs -l app.kubernetes.io/instance=$RELEASE_NAME -n $NAMESPACE -f"
echo "  • Port forward: kubectl port-forward svc/$RELEASE_NAME 8080:80 -n $NAMESPACE"
echo "  • Uninstall: helm uninstall $RELEASE_NAME -n $NAMESPACE"
