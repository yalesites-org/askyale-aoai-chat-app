#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "Usage: $0 --app <app-name> --rg <resource-group> --repo <github-url> --branch <branch>"
    echo "           [--force] [--dry-run]"
    echo ""
    echo "Configure an Azure App Service for GitHub source deployment."
    echo ""
    echo "Required:"
    echo "  --app       Azure App Service name"
    echo "  --rg        Azure resource group"
    echo "  --repo      GitHub repository URL (public)"
    echo "  --branch    Branch to deploy"
    echo ""
    echo "Optional:"
    echo "  --force     Skip confirmation when switching from non-Python runtime"
    echo "  --dry-run   Print commands without executing mutations"
    exit 1
}

APP_NAME=""
RESOURCE_GROUP=""
REPO_URL=""
BRANCH=""
FORCE=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --app) APP_NAME="$2"; shift 2 ;;
        --rg) RESOURCE_GROUP="$2"; shift 2 ;;
        --repo) REPO_URL="$2"; shift 2 ;;
        --branch) BRANCH="$2"; shift 2 ;;
        --force) FORCE=true; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

if [[ -z "$APP_NAME" || -z "$RESOURCE_GROUP" || -z "$REPO_URL" || -z "$BRANCH" ]]; then
    echo "Error: --app, --rg, --repo, and --branch are all required."
    usage
fi

run_cmd() {
    if [[ "$DRY_RUN" == true ]]; then
        echo "[DRY RUN] $*"
    else
        "$@"
    fi
}

echo "=== Step 1: Validating prerequisites ==="

if ! command -v az &> /dev/null; then
    echo "Error: Azure CLI (az) is not installed."
    exit 1
fi

if ! az account show &> /dev/null; then
    echo "Error: Not authenticated. Run 'az login' first."
    exit 1
fi

if ! az webapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    echo "Error: App '$APP_NAME' not found in resource group '$RESOURCE_GROUP'."
    exit 1
fi

echo "App '$APP_NAME' found in resource group '$RESOURCE_GROUP'."

echo ""
echo "=== Step 2: Checking current deployment source ==="

SOURCE_INFO=$(az webapp deployment source show \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --output json 2>/dev/null || true)

if [[ -n "$SOURCE_INFO" && "$SOURCE_INFO" != "null" ]]; then
    echo "Current source:"
    echo "$SOURCE_INFO" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f\"  Repo:   {d.get('repoUrl', 'N/A')}\")
print(f\"  Branch: {d.get('branch', 'N/A')}\")
print(f\"  Manual: {d.get('isManualIntegration', 'N/A')}\")
" 2>/dev/null || echo "  (unable to parse source info)"
else
    echo "No deployment source currently configured."
fi

echo ""
echo "=== Step 3: Checking runtime ==="

RUNTIME=$(az webapp config show \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "linuxFxVersion" \
    --output tsv 2>/dev/null || true)

echo "Current runtime: ${RUNTIME:-"(not set)"}"

if [[ "$RUNTIME" == PYTHON\|* ]]; then
    echo "Already using Python runtime. Skipping switch."
else
    echo ""
    echo "WARNING: App is not using the Python runtime."
    echo "Current value: ${RUNTIME:-"(empty)"}"
    echo "This script will switch to PYTHON|3.11 and set the startup command."

    if [[ "$FORCE" != true && "$DRY_RUN" != true ]]; then
        read -r -p "Continue? (y/N) " confirm
        if [[ "$confirm" != [yY] ]]; then
            echo "Aborted."
            exit 1
        fi
    fi

    echo "Switching to PYTHON|3.11..."
    run_cmd az webapp config set \
        --name "$APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --linux-fx-version "PYTHON|3.11"

    echo "Setting startup command..."
    run_cmd az webapp config set \
        --name "$APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --startup-file "gunicorn app:app -w 3 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000"
fi

echo ""
echo "=== Step 4: Disconnecting existing deployment source ==="
run_cmd az webapp deployment source delete \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" || true

echo ""
echo "=== Step 5: Enabling Oryx build during deployment ==="
run_cmd az webapp config appsettings set \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --settings SCM_DO_BUILD_DURING_DEPLOYMENT="true"

echo ""
echo "=== Step 6: Configuring GitHub as deployment source ==="
echo "This triggers an initial fetch and build, which may take several minutes for large repos."
run_cmd az webapp deployment source config \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --repo-url "$REPO_URL" \
    --branch "$BRANCH" \
    --manual-integration

# Verify the source was configured correctly
if [[ "$DRY_RUN" != true ]]; then
    CONFIGURED_BRANCH=$(az webapp deployment source show \
        --name "$APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query "branch" \
        --output tsv 2>/dev/null || true)

    if [[ -z "$CONFIGURED_BRANCH" || "$CONFIGURED_BRANCH" == "null" ]]; then
        echo ""
        echo "WARNING: Branch was not set after source config. The initial fetch may have"
        echo "timed out (common with large repos). Try running deploy-sync.sh to retry."
        exit 1
    fi
fi

echo ""
echo "=== Step 7: Waiting for deployment ==="
if [[ "$DRY_RUN" != true ]]; then
    echo "Polling deployment status..."
    for i in $(seq 1 30); do
        STATUS=$(az webapp log deployment list \
            --name "$APP_NAME" \
            --resource-group "$RESOURCE_GROUP" \
            --query "[0].{status: status, complete: complete}" \
            --output json 2>/dev/null || echo '{}')

        COMPLETE=$(echo "$STATUS" | python3 -c "import sys,json; print(json.load(sys.stdin).get('complete', False))" 2>/dev/null || echo "False")

        if [[ "$COMPLETE" == "True" ]]; then
            echo "Deployment complete."
            break
        fi

        if [[ $i -eq 30 ]]; then
            echo "Deployment still in progress after 5 minutes."
            echo "The Oryx build may still be running. Check status with deploy-sync.sh or:"
            echo "  az webapp log deployment list --name $APP_NAME --resource-group $RESOURCE_GROUP --output table"
            break
        fi

        sleep 10
    done

    echo ""
    az webapp log deployment list \
        --name "$APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --output table
fi

echo ""
echo "To tail logs, run:"
echo "  az webapp log tail --name \"$APP_NAME\" --resource-group \"$RESOURCE_GROUP\""
