#!/bin/bash

################################################################################
# Sync Script: yale-development → ai_engine_chat
#
# This script synchronizes the React frontend from the yale-development
# repository to the ai_engine_chat Drupal module deployment location.
#
# Usage:
#   ./scripts/sync-to-drupal.sh [OPTIONS]
#
# Options:
#   --dry-run                Show what would be synced without making changes
#   --skip-build             Skip the build verification step
#   --auto-commit            Automatically commit changes in ai_engine repository
#   --ai-engine-path PATH    Override the ai_engine repository location
#
# Environment Variables:
#   AI_ENGINE_PATH          Path to ai_engine repository (overrides default)
#
# Configuration:
#   You can set AI_ENGINE_PATH in your shell profile (~/.bashrc, ~/.zshrc):
#     export AI_ENGINE_PATH="/path/to/your/ai_engine"
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default Configuration
# Try to detect yale-development root (assume script is in scripts/ subdirectory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
YALE_DEV_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default ai_engine location (can be overridden)
DEFAULT_AI_ENGINE_ROOT="$HOME/code/ai_engine/modules/ai_engine_chat"

# Use environment variable if set, otherwise use default
AI_ENGINE_ROOT="${AI_ENGINE_PATH:-$DEFAULT_AI_ENGINE_ROOT}"

FRONTEND_SRC="${YALE_DEV_ROOT}/frontend"
REACT_DEST="${AI_ENGINE_ROOT}/react"

# Parse command line arguments
DRY_RUN=false
SKIP_BUILD=false
AUTO_COMMIT=false
CUSTOM_AI_ENGINE_PATH=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --skip-build)
      SKIP_BUILD=true
      shift
      ;;
    --auto-commit)
      AUTO_COMMIT=true
      shift
      ;;
    --ai-engine-path)
      CUSTOM_AI_ENGINE_PATH="$2"
      shift 2
      ;;
    --help|-h)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --dry-run                Show what would be synced without making changes"
      echo "  --skip-build             Skip the build verification step"
      echo "  --auto-commit            Automatically commit changes in ai_engine repository"
      echo "  --ai-engine-path PATH    Override the ai_engine repository location"
      echo "  --help, -h               Show this help message"
      echo ""
      echo "Environment Variables:"
      echo "  AI_ENGINE_PATH           Path to ai_engine repository (overrides default)"
      echo ""
      echo "Default ai_engine location: $DEFAULT_AI_ENGINE_ROOT"
      echo "Current ai_engine location: $AI_ENGINE_ROOT"
      echo ""
      echo "Examples:"
      echo "  $0 --dry-run"
      echo "  $0 --ai-engine-path /custom/path/to/ai_engine/modules/ai_engine_chat"
      echo "  AI_ENGINE_PATH=/custom/path $0"
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown argument: $1${NC}"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Apply custom path if provided via command line (highest priority)
if [ -n "$CUSTOM_AI_ENGINE_PATH" ]; then
  AI_ENGINE_ROOT="$CUSTOM_AI_ENGINE_PATH"
  REACT_DEST="${AI_ENGINE_ROOT}/react"
fi

################################################################################
# Helper Functions
################################################################################

print_header() {
  echo -e "\n${BLUE}===================================================${NC}"
  echo -e "${BLUE}$1${NC}"
  echo -e "${BLUE}===================================================${NC}\n"
}

print_success() {
  echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
  echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
  echo -e "${RED}✗ $1${NC}"
}

print_info() {
  echo -e "${BLUE}ℹ $1${NC}"
}

################################################################################
# Configuration Display
################################################################################

print_header "Configuration"

print_info "Yale Development Root:"
echo "  $YALE_DEV_ROOT"
print_info "AI Engine Root:"
echo "  $AI_ENGINE_ROOT"
print_info "Frontend Source:"
echo "  $FRONTEND_SRC"
print_info "React Destination:"
echo "  $REACT_DEST"

if [ -n "$CUSTOM_AI_ENGINE_PATH" ]; then
  print_warning "Using custom ai_engine path from command line"
elif [ -n "$AI_ENGINE_PATH" ]; then
  print_warning "Using ai_engine path from AI_ENGINE_PATH environment variable"
else
  print_info "Using default ai_engine path"
fi

################################################################################
# Preflight Checks
################################################################################

print_header "Preflight Checks"

# Check if source directory exists
if [ ! -d "$FRONTEND_SRC" ]; then
  print_error "Source directory not found: $FRONTEND_SRC"
  exit 1
fi
print_success "Source directory found: $FRONTEND_SRC"

# Check if destination directory exists
if [ ! -d "$REACT_DEST" ]; then
  print_error "Destination directory not found: $REACT_DEST"
  print_info "Expected location: $REACT_DEST"
  echo ""
  print_info "You can specify a custom location using:"
  echo "  --ai-engine-path /path/to/ai_engine/modules/ai_engine_chat"
  echo "Or set the AI_ENGINE_PATH environment variable"
  exit 1
fi
print_success "Destination directory found: $REACT_DEST"

# Check if we're in the correct git repository
cd "$YALE_DEV_ROOT" || exit 1
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "yale-development" ]; then
  print_warning "Not on yale-development branch (currently on: $CURRENT_BRANCH)"
  read -p "Continue anyway? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_info "Sync cancelled"
    exit 0
  fi
else
  print_success "On yale-development branch"
fi

# Check for uncommitted changes in yale-development
if ! git diff-index --quiet HEAD --; then
  print_warning "You have uncommitted changes in yale-development"
  read -p "Continue anyway? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_info "Sync cancelled. Please commit your changes first."
    exit 0
  fi
fi

################################################################################
# Build Verification
################################################################################

if [ "$SKIP_BUILD" = false ]; then
  print_header "Build Verification"

  cd "$FRONTEND_SRC" || exit 1

  # Check if node_modules exists
  if [ ! -d "node_modules" ]; then
    print_info "node_modules not found. Running npm install..."
    npm install
  fi

  # Run build to verify code compiles
  print_info "Running build to verify code..."
  if npm run build; then
    print_success "Build successful"
  else
    print_error "Build failed. Please fix errors before syncing."
    exit 1
  fi
else
  print_warning "Skipping build verification"
fi

################################################################################
# Sync Operation
################################################################################

print_header "Synchronizing Files"

# Build rsync command
RSYNC_CMD="rsync -av --delete"
RSYNC_CMD="$RSYNC_CMD --exclude 'node_modules'"
RSYNC_CMD="$RSYNC_CMD --exclude '.git'"
RSYNC_CMD="$RSYNC_CMD --exclude 'dist'"
RSYNC_CMD="$RSYNC_CMD --exclude '.DS_Store'"
RSYNC_CMD="$RSYNC_CMD --exclude '*.log'"

if [ "$DRY_RUN" = true ]; then
  RSYNC_CMD="$RSYNC_CMD --dry-run"
  print_warning "DRY RUN MODE - No files will be changed"
fi

print_info "Syncing from:"
echo "  $FRONTEND_SRC"
print_info "Syncing to:"
echo "  $REACT_DEST"
echo ""

# Execute rsync
if $RSYNC_CMD "$FRONTEND_SRC/" "$REACT_DEST/"; then
  print_success "Files synced successfully"
else
  print_error "Sync failed"
  exit 1
fi

if [ "$DRY_RUN" = true ]; then
  print_info "Dry run complete. No files were modified."
  exit 0
fi

################################################################################
# Git Status in ai_engine
################################################################################

print_header "Git Status in ai_engine"

cd "$AI_ENGINE_ROOT" || exit 1

# Check if there are changes
if git diff-index --quiet HEAD --; then
  print_info "No changes detected in ai_engine repository"
  print_success "Sync complete - repositories are already in sync"
  exit 0
fi

# Show git status
print_info "Changes detected:"
git status --short

################################################################################
# Commit Changes (if --auto-commit)
################################################################################

if [ "$AUTO_COMMIT" = true ]; then
  print_header "Auto-Commit Changes"

  # Get the latest commit message from yale-development
  cd "$YALE_DEV_ROOT" || exit 1
  LATEST_COMMIT_MSG=$(git log -1 --pretty=%B | head -n 1)

  cd "$AI_ENGINE_ROOT" || exit 1

  COMMIT_MSG="feat: sync from yale-development

Synced changes from yale-development repository.
Latest yale-development commit: $LATEST_COMMIT_MSG

Auto-generated by sync-to-drupal.sh"

  git add react/

  if git commit -m "$COMMIT_MSG"; then
    print_success "Changes committed in ai_engine repository"
    print_info "Commit message:"
    echo "$COMMIT_MSG"

    print_warning "Don't forget to push: cd $AI_ENGINE_ROOT && git push"
  else
    print_error "Commit failed"
    exit 1
  fi
else
  print_header "Next Steps"

  echo -e "${YELLOW}Changes have been synced but not committed.${NC}"
  echo ""
  echo "To review and commit the changes:"
  echo -e "  ${BLUE}cd $AI_ENGINE_ROOT${NC}"
  echo -e "  ${BLUE}git diff${NC}"
  echo -e "  ${BLUE}git add react/${NC}"
  echo -e "  ${BLUE}git commit -m 'feat: sync from yale-development - [describe changes]'${NC}"
  echo -e "  ${BLUE}git push${NC}"
  echo ""
  echo "Or run this script again with --auto-commit to commit automatically"
fi

################################################################################
# Summary
################################################################################

print_header "Sync Complete"

print_success "Frontend synced from yale-development to ai_engine_chat"
print_info "Source: $FRONTEND_SRC"
print_info "Destination: $REACT_DEST"

if [ "$AUTO_COMMIT" = false ]; then
  print_warning "Remember to commit and push changes in ai_engine repository"
fi

echo ""
