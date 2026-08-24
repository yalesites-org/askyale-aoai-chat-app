#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "Usage: $0 --app <app-name> --rg <resource-group>"
    echo ""
    echo "Trigger a deployment sync on an Azure App Service."
    echo ""
    echo "Required:"
    echo "  --app     Azure App Service name"
    echo "  --rg      Azure resource group"
    exit 1
}

APP_NAME=""
RESOURCE_GROUP=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --app) APP_NAME="$2"; shift 2 ;;
        --rg) RESOURCE_GROUP="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

if [[ -z "$APP_NAME" || -z "$RESOURCE_GROUP" ]]; then
    echo "Error: --app and --rg are required."
    usage
fi

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
echo "=== Step 2: Triggering deployment sync ==="
az webapp deployment source sync \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP"

echo ""
echo "=== Step 3: Deployment status ==="
az webapp log deployment list \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --output table

echo ""
echo "Sync triggered. The deployment may still be in progress."
echo "To tail logs, run:"
echo "  az webapp log tail --name $APP_NAME --resource-group $RESOURCE_GROUP"
