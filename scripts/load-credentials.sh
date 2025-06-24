#!/bin/bash

# Yuga Planner Credential Loading Script
# This script loads credentials from environment variables or creds.py

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

# Function to check and validate required credentials
check_credentials() {
    echo "🔍 Checking for credentials..."

    local missing_vars=()
    local required_vars=("NEBIUS_API_KEY" "NEBIUS_MODEL" "MODAL_TOKEN_ID" "MODAL_TOKEN_SECRET" "HF_MODEL" "HF_TOKEN")

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
            return 1
        fi
    fi

    echo "✅ All credentials found"
    return 0
}

# Main execution when script is run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    check_credentials
    exit $?
fi
