#!/bin/bash
set -e

# Yuga Planner Kubernetes Deployment Script
# This script loads credentials from environment variables or creds.py and deploys to Kubernetes

echo "🚀 Deploying Yuga Planner to Kubernetes..."

# Check if we're in the correct directory (project root)
if [ ! -f "deploy/kubernetes.yaml" ]; then
    echo "❌ Error: kubernetes.yaml not found. Please run this script from the project root."
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

# Check if envsubst is available
if ! command -v envsubst &> /dev/null; then
    echo "❌ Error: envsubst is required but not installed. Please install gettext-base package."
    exit 1
fi

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ Error: kubectl is required but not installed."
    exit 1
fi

# Substitute environment variables and apply to Kubernetes
echo "🔧 Substituting environment variables and deploying..."
envsubst < deploy/kubernetes.yaml | kubectl apply -f -

echo "✅ Deployment complete!"
echo "🌐 Access the application at: http://<node-ip>:30860"
echo "🔍 Check deployment status: kubectl get pods -l app=yuga-planner"
echo "📋 View logs: kubectl logs -l app=yuga-planner -f"
