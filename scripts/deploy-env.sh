#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "Usage: $0 --app <app-name> --rg <resource-group> --env-file <path> [--dry-run]"
    echo ""
    echo "Push environment variables from a .env file to Azure App Service app settings."
    echo ""
    echo "Required:"
    echo "  --app        Azure App Service name"
    echo "  --rg         Azure resource group"
    echo "  --env-file   Path to .env file (KEY=VALUE format)"
    echo ""
    echo "Optional:"
    echo "  --dry-run    Print keys that would be set without executing"
    exit 1
}

APP_NAME=""
RESOURCE_GROUP=""
ENV_FILE=""
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --app) APP_NAME="$2"; shift 2 ;;
        --rg) RESOURCE_GROUP="$2"; shift 2 ;;
        --env-file) ENV_FILE="$2"; shift 2 ;;
        --dry-run) DRY_RUN=true; shift ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

if [[ -z "$APP_NAME" || -z "$RESOURCE_GROUP" || -z "$ENV_FILE" ]]; then
    echo "Error: --app, --rg, and --env-file are all required."
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

if [[ ! -f "$ENV_FILE" ]]; then
    echo "Error: File not found: $ENV_FILE"
    exit 1
fi

if [[ ! -r "$ENV_FILE" ]]; then
    echo "Error: Cannot read file: $ENV_FILE"
    exit 1
fi

if git rev-parse --git-dir &>/dev/null; then
    if ! git check-ignore -q "$ENV_FILE" 2>/dev/null; then
        echo "Warning: '$ENV_FILE' is not in .gitignore. Ensure it is not committed to avoid leaking secrets."
    fi
fi

echo "App '$APP_NAME' found. Reading env file: $ENV_FILE"

echo ""
echo "=== Step 2: Parsing env file ==="

SETTINGS=()
LINE_NUM=0

while IFS= read -r line || [[ -n "$line" ]]; do
    LINE_NUM=$((LINE_NUM + 1))

    # Skip blank lines and comments
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue

    # Validate KEY=VALUE format
    if [[ ! "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
        echo "Warning: Skipping malformed line $LINE_NUM"
        continue
    fi

    KEY="${line%%=*}"
    VALUE="${line#*=}"
    VALUE="${VALUE%$'\r'}"

    # Strip matching surrounding quotes from value
    if [[ "${VALUE:0:1}" == '"' && "${VALUE: -1}" == '"' ]]; then
        VALUE="${VALUE:1:${#VALUE}-2}"
    elif [[ "${VALUE:0:1}" == "'" && "${VALUE: -1}" == "'" ]]; then
        VALUE="${VALUE:1:${#VALUE}-2}"
    fi

    SETTINGS+=("${KEY}=${VALUE}")
done < "$ENV_FILE"

if [[ ${#SETTINGS[@]} -eq 0 ]]; then
    echo "No settings found in $ENV_FILE."
    exit 0
fi

echo ""
echo "=== Step 3: Settings to push (${#SETTINGS[@]} keys) ==="
for setting in "${SETTINGS[@]}"; do
    echo "  ${setting%%=*}"
done

if [[ "$DRY_RUN" == true ]]; then
    echo ""
    echo "[DRY RUN] Would push ${#SETTINGS[@]} settings to $APP_NAME."
    exit 0
fi

echo ""
echo "=== Step 4: Pushing settings ==="
az webapp config appsettings set \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --settings "${SETTINGS[@]}" \
    --output none

echo ""
echo "=== Step 5: Verifying ==="
az webapp config appsettings list \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "[].name" \
    --output tsv | sort

echo ""
echo "Done. ${#SETTINGS[@]} settings pushed to $APP_NAME."
