#!/bin/bash
set -e

# Yuga Planner Kubernetes Cleanup Script
# This script removes all Kubernetes resources created by the deployment

echo "🧹 Cleaning up Yuga Planner Kubernetes deployment..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ Error: kubectl is required but not installed."
    exit 1
fi

# Check if we're in the correct directory (project root)
if [ ! -f "deploy/kubernetes.yaml" ]; then
    echo "❌ Error: kubernetes.yaml not found. Please run this script from the project root."
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
        echo "ℹ️  No Yuga Planner resources found in the current namespace."
        return 1
    fi

    return 0
}

# Check if any resources exist
if ! check_resources; then
    echo "✅ Nothing to clean up."
    exit 0
fi

# Show what will be deleted
echo "🔍 Found the following Yuga Planner resources:"
kubectl get deployment,service,secret,configmap -l app=yuga-planner 2>/dev/null || true

# Confirm deletion
read -p "❓ Are you sure you want to delete these resources? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cleanup cancelled."
    exit 0
fi

echo "🗑️  Deleting Kubernetes resources..."

# Delete resources by label selector (safer approach)
echo "  • Deleting deployment..."
kubectl delete deployment -l app=yuga-planner --ignore-not-found=true

echo "  • Deleting service..."
kubectl delete service -l app=yuga-planner --ignore-not-found=true

echo "  • Deleting secrets..."
kubectl delete secret -l app=yuga-planner --ignore-not-found=true

echo "  • Deleting configmaps..."
kubectl delete configmap -l app=yuga-planner --ignore-not-found=true

echo "✅ Cleanup complete!"
echo "🔍 Verify cleanup: kubectl get all -l app=yuga-planner"
