#!/bin/bash
set -e

# Yuga Planner Helm Cleanup Script
# This script removes the Helm release and all associated resources

echo "🧹 Cleaning up Yuga Planner Helm deployment..."

# Check if helm is available
if ! command -v helm &> /dev/null; then
    echo "❌ Error: helm is required but not installed."
    echo "💡 Install Helm from: https://helm.sh/docs/intro/install/"
    exit 1
fi

# Configuration (same defaults as deploy script)
RELEASE_NAME="${HELM_RELEASE_NAME:-yuga-planner}"
# Get current namespace, fallback to default if not set
CURRENT_NAMESPACE=$(kubectl config view --minify --output 'jsonpath={..namespace}' 2>/dev/null || echo "default")
NAMESPACE="${HELM_NAMESPACE:-$CURRENT_NAMESPACE}"

echo "📦 Helm Release: $RELEASE_NAME"
echo "🏷️  Namespace: $NAMESPACE"

# Check if the release exists
if ! helm list -n "$NAMESPACE" | grep -q "^$RELEASE_NAME"; then
    echo "ℹ️  Helm release '$RELEASE_NAME' not found in namespace '$NAMESPACE'."
    echo "✅ Nothing to clean up."
    exit 0
fi

# Show release information
echo "🔍 Found Helm release:"
helm list -n "$NAMESPACE" | grep "^$RELEASE_NAME" || true

echo ""
echo "📊 Release details:"
helm status "$RELEASE_NAME" -n "$NAMESPACE" || true

# Confirm deletion
echo ""
read -p "❓ Are you sure you want to uninstall the Helm release '$RELEASE_NAME'? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cleanup cancelled."
    exit 0
fi

echo "🗑️  Uninstalling Helm release..."
helm uninstall "$RELEASE_NAME" -n "$NAMESPACE"

echo "✅ Helm release uninstalled successfully!"

# Check if namespace should be cleaned up (optional)
if [ "$NAMESPACE" != "default" ]; then
    echo ""
    echo "🤔 The namespace '$NAMESPACE' still exists."
    read -p "❓ Do you want to delete the namespace '$NAMESPACE' as well? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Check if namespace has other resources
        OTHER_RESOURCES=$(kubectl get all -n "$NAMESPACE" --ignore-not-found=true 2>/dev/null | grep -v "^NAME" | wc -l)
        if [ "$OTHER_RESOURCES" -gt 0 ]; then
            echo "⚠️  Warning: Namespace '$NAMESPACE' contains other resources."
            kubectl get all -n "$NAMESPACE" 2>/dev/null || true
            read -p "❓ Are you sure you want to delete the entire namespace? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                kubectl delete namespace "$NAMESPACE"
                echo "✅ Namespace '$NAMESPACE' deleted."
            else
                echo "ℹ️  Namespace '$NAMESPACE' preserved."
            fi
        else
            kubectl delete namespace "$NAMESPACE"
            echo "✅ Empty namespace '$NAMESPACE' deleted."
        fi
    else
        echo "ℹ️  Namespace '$NAMESPACE' preserved."
    fi
fi

echo ""
echo "🔍 Useful commands to verify cleanup:"
echo "  • List remaining releases: helm list -A"
echo "  • Check for remaining resources: kubectl get all -l app.kubernetes.io/instance=$RELEASE_NAME -A"
