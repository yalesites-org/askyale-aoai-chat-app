# Sync Scripts Usage Guide

## Overview

This guide explains how to use the sync script to keep yale-development and ai_engine_chat in sync.

## Quick Reference

```bash
# Preview changes before syncing
./scripts/sync-to-drupal.sh --dry-run

# Perform sync
./scripts/sync-to-drupal.sh

# Sync with auto-commit
./scripts/sync-to-drupal.sh --auto-commit

# Custom ai_engine location
./scripts/sync-to-drupal.sh --ai-engine-path /custom/path/to/ai_engine/modules/ai_engine_chat
```

## Configuration

The script supports three ways to configure the ai_engine location (in order of priority):

### 1. Command Line Argument (Highest Priority)

```bash
./scripts/sync-to-drupal.sh --ai-engine-path /custom/path/to/ai_engine/modules/ai_engine_chat
```

### 2. Environment Variable

**One-time use:**
```bash
AI_ENGINE_PATH=/custom/path/to/ai_engine/modules/ai_engine_chat ./scripts/sync-to-drupal.sh
```

**Persistent configuration** - Add to `~/.bashrc` or `~/.zshrc`:
```bash
export AI_ENGINE_PATH="/Users/yourname/custom/path/ai_engine/modules/ai_engine_chat"
```

Then reload your shell:
```bash
source ~/.zshrc  # or ~/.bashrc
```

### 3. Default Location

If no custom path is provided:
```
$HOME/code/ai_engine/modules/ai_engine_chat
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview what would be synced without making changes |
| `--skip-build` | Skip the build verification step (faster but riskier) |
| `--auto-commit` | Automatically commit changes in ai_engine repository |
| `--ai-engine-path PATH` | Override the ai_engine repository location |
| `--help`, `-h` | Show help message with all options |

## Usage Examples

### Example 1: Preview Changes Before Syncing

```bash
./scripts/sync-to-drupal.sh --dry-run
```

This shows you exactly which files would be updated without making any changes.

### Example 2: Different Directory Structure

If your ai_engine is in a different location:

```bash
./scripts/sync-to-drupal.sh --ai-engine-path /Users/sarah/projects/drupal/ai_engine/modules/ai_engine_chat
```

### Example 3: Quick Sync with Auto-Commit

```bash
./scripts/sync-to-drupal.sh --auto-commit
```

This will:
1. Verify build succeeds
2. Sync files
3. Automatically commit with a descriptive message
4. Remind you to push

### Example 4: Fast Sync (Skip Build)

```bash
./scripts/sync-to-drupal.sh --skip-build
```

⚠️ **Warning:** Only use `--skip-build` if you're confident the code builds correctly.

## Typical Workflow

### Standard Development Workflow

```bash
# 1. Make changes to frontend code
cd /Users/db2553/code/askyale-aoai-chat-app
git checkout yale-development

# Edit files in frontend/src/...

# 2. Test your changes locally
cd frontend
npm run dev

# 3. Commit your changes in yale-development
git add .
git commit -m "feat: add new chat feature"
git push origin yale-development

# 4. Preview sync to ai_engine
cd ..
./scripts/sync-to-drupal.sh --dry-run

# 5. Perform actual sync
./scripts/sync-to-drupal.sh

# 6. Review and commit in ai_engine
cd /Users/db2553/code/ai_engine/modules/ai_engine_chat
git diff  # Review changes
git add react/
git commit -m "feat: sync from yale-development - add new chat feature"
git push
```

### Quick Sync Workflow

For experienced developers:

```bash
cd /Users/db2553/code/askyale-aoai-chat-app
./scripts/sync-to-drupal.sh --auto-commit

cd /Users/db2553/code/ai_engine/modules/ai_engine_chat
git push
```

## What Gets Synced

The script syncs everything from `frontend/` to `react/` **except**:

- ❌ `node_modules/` - Dependencies (run `npm install` after sync)
- ❌ `.git/` - Git history
- ❌ `dist/` - Build output
- ❌ `.DS_Store` - macOS metadata
- ❌ `*.log` - Log files

## Error Handling

### Source directory not found

```
✗ Source directory not found: /path/to/frontend
```

**Solution:** Run the script from the yale-development repository root:
```bash
cd /Users/db2553/code/askyale-aoai-chat-app
./scripts/sync-to-drupal.sh
```

### Destination directory not found

```
✗ Destination directory not found: /path/to/react
```

**Solution:** Specify the correct ai_engine location:
```bash
./scripts/sync-to-drupal.sh --ai-engine-path /correct/path/to/ai_engine/modules/ai_engine_chat
```

### Not on yale-development branch

```
⚠ Not on yale-development branch (currently on: main)
```

**Solution:** Checkout yale-development or confirm you want to sync from a different branch:
```bash
git checkout yale-development
```

### Uncommitted changes

```
⚠ You have uncommitted changes in yale-development
```

**Solution:** Commit or stash your changes:
```bash
git add .
git commit -m "feat: your changes"
```

### Build failed

```
✗ Build failed. Please fix errors before syncing.
```

**Solution:** Fix build errors in your frontend code:
```bash
cd frontend
npm run build  # See the errors
# Fix the errors
npm run build  # Verify it works
```

## Testing After Sync

After syncing to ai_engine_chat:

```bash
cd /Users/db2553/code/ai_engine/modules/ai_engine_chat/react

# Install dependencies (if package.json changed)
npm install

# Build for production
npm run build

# Test in your Drupal site
```

## Team Configuration Examples

Each developer can set their own path:

**Developer 1 (~/.zshrc):**
```bash
export AI_ENGINE_PATH="/Users/dev1/work/ai_engine/modules/ai_engine_chat"
```

**Developer 2 (~/.zshrc):**
```bash
export AI_ENGINE_PATH="/Users/dev2/projects/drupal/ai_engine/modules/ai_engine_chat"
```

**CI/CD environment:**
```bash
export AI_ENGINE_PATH="/var/www/drupal/modules/custom/ai_engine/modules/ai_engine_chat"
```

## Best Practices

1. ✅ **Always test before syncing**
   ```bash
   cd frontend && npm run dev && npm run build
   ```

2. ✅ **Use dry-run first for significant changes**
   ```bash
   ./scripts/sync-to-drupal.sh --dry-run
   ```

3. ✅ **Review changes before pushing**
   ```bash
   cd /path/to/ai_engine && git diff
   ```

4. ✅ **Keep commits atomic**
   - Make related changes together
   - Sync after each logical unit of work
   - Write clear commit messages

5. ✅ **Test in Drupal after syncing**
   - Don't assume it works without testing
   - Check browser console for errors
   - Test all affected features

## Troubleshooting

### Files synced but build fails in ai_engine

**Cause:** Dependencies might have changed

**Solution:**
```bash
cd /path/to/ai_engine/modules/ai_engine_chat/react
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Sync seems to skip files

**Cause:** Files might be in excluded directories

**Solution:** Check that files aren't in `node_modules/`, `.git/`, or `dist/`

## Getting Help

```bash
# Show all options and current configuration
./scripts/sync-to-drupal.sh --help
```

## Related Documentation

- [CODEBASE_SYNC.md](CODEBASE_SYNC.md) - Overall synchronization strategy and workflow
- Repository structure and relationships
- Upstream sync procedures
