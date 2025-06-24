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

# Function to load credentials from creds.py if environment variables are not set
load_credentials() {
    local creds_file="tests/secrets/creds.py"

    if [ -f "$creds_file" ]; then
        echo "📋 Loading credentials from $creds_file..."

        # Extract credentials from creds.py if environment variables are not set
        if [ -z "$NEBIUS_API_KEY" ]; then
            export NEBIUS_API_KEY=$(python3 -c "
import sys
sys.path.append('tests/secrets')
import creds
print(creds.NEBIUS_API_KEY)
" 2>/dev/null || echo "")
        fi

        if [ -z "$NEBIUS_MODEL" ]; then
            export NEBIUS_MODEL=$(python3 -c "
import sys
sys.path.append('tests/secrets')
import creds
print(creds.NEBIUS_MODEL)
" 2>/dev/null || echo "")
        fi

        if [ -z "$MODAL_TOKEN_ID" ]; then
            export MODAL_TOKEN_ID=$(python3 -c "
import sys
sys.path.append('tests/secrets')
import creds
print(creds.MODAL_TOKEN_ID)
" 2>/dev/null || echo "")
        fi

        if [ -z "$MODAL_TOKEN_SECRET" ]; then
            export MODAL_TOKEN_SECRET=$(python3 -c "
import sys
sys.path.append('tests/secrets')
import creds
print(creds.MODAL_TOKEN_SECRET)
" 2>/dev/null || echo "")
        fi

        if [ -z "$HF_MODEL" ]; then
            export HF_MODEL=$(python3 -c "
import sys
sys.path.append('tests/secrets')
import creds
print(creds.HF_MODEL)
" 2>/dev/null || echo "")
        fi

        if [ -z "$HF_TOKEN" ]; then
            export HF_TOKEN=$(python3 -c "
import sys
sys.path.append('tests/secrets')
import creds
print(creds.HF_TOKEN)
" 2>/dev/null || echo "")
        fi
    else
        echo "⚠️  Warning: $creds_file not found"
    fi
}

# Check if credentials are available in environment variables
echo "🔍 Checking for credentials..."

missing_vars=()
required_vars=("NEBIUS_API_KEY" "NEBIUS_MODEL" "MODAL_TOKEN_ID" "MODAL_TOKEN_SECRET" "HF_MODEL" "HF_TOKEN")

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -gt 0 ]; then
    echo "📂 Missing environment variables: ${missing_vars[*]}"
    echo "🔄 Attempting to load from creds.py..."
    load_credentials

    # Check again after loading from creds.py
    missing_vars=()
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done

    if [ ${#missing_vars[@]} -gt 0 ]; then
        echo "❌ Error: The following required environment variables are not set: ${missing_vars[*]}"
        echo "💡 Please set them in your environment or ensure tests/secrets/creds.py exists with the required values."
        exit 1
    fi
fi

echo "✅ All credentials found"

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
