#!/bin/bash

# Colors and formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

# Yuga Planner Credential Loading Script
# This script loads credentials from environment variables or creds.py

# Function to load credentials from creds.py if environment variables are not set
load_credentials() {
    local creds_file="tests/secrets/creds.py"

    if [ -f "$creds_file" ]; then
        echo -e "${BLUE}📋 Loading credentials from $creds_file...${RESET}"

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
        echo -e "${YELLOW}⚠️  Warning: $creds_file not found${RESET}"
        echo -e "${CYAN}💡 Run '${GREEN}make setup-secrets${CYAN}' to create the template${RESET}"
    fi
}

# Function to check and validate required credentials
check_credentials() {
    echo -e "${CYAN}🔍 Validating credentials...${RESET}"

    local missing_vars=()
    local required_vars=("NEBIUS_API_KEY" "NEBIUS_MODEL" "MODAL_TOKEN_ID" "MODAL_TOKEN_SECRET" "HF_MODEL" "HF_TOKEN")
    local found_vars=()

    # First check what's already available
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        else
            found_vars+=("$var")
        fi
    done

    # Show what we found
    if [ ${#found_vars[@]} -gt 0 ]; then
        echo -e "${GREEN}✅ Found environment variables: ${found_vars[*]}${RESET}"
    fi

    if [ ${#missing_vars[@]} -gt 0 ]; then
        echo -e "${YELLOW}📂 Missing from environment: ${missing_vars[*]}${RESET}"
        echo -e "${BLUE}🔄 Attempting to load from creds.py...${RESET}"
        load_credentials

        # Check again after loading from creds.py
        missing_vars=()
        for var in "${required_vars[@]}"; do
            if [ -z "${!var}" ]; then
                missing_vars+=("$var")
            fi
        done

        if [ ${#missing_vars[@]} -gt 0 ]; then
            echo ""
            echo -e "${RED}❌ Error: Missing required credentials: ${missing_vars[*]}${RESET}"
            echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
            echo -e "${BOLD}💡 Setup Instructions:${RESET}"
            echo -e "  1. Run: ${GREEN}make setup-secrets${RESET}"
            echo -e "  2. Edit: ${CYAN}tests/secrets/creds.py${RESET}"
            echo -e "  3. Add your API credentials"
            echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
            return 1
        fi
    fi

    echo -e "${GREEN}✅ All credentials validated successfully${RESET}"
    return 0
}

# Main execution when script is run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo -e "${BOLD}🔐 Yuga Planner - Credential Validator${RESET}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    check_credentials
    exit $?
fi
