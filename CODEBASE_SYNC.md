# Codebase Synchronization Documentation

## Overview

This repository (`askyale-aoai-chat-app`) is a fork of the Microsoft Azure OpenAI Chat App sample. It serves as the **source of truth** for the React frontend that is deployed as part of the `ai_engine_chat` Drupal module.

## Repository Relationships

### Primary Repository (Source of Truth)
- **Location**: `/Users/db2553/code/askyale-aoai-chat-app`
- **Remote**: `git@github.com:yalesites-org/askyale-aoai-chat-app.git`
- **Branch**: `yale-development`
- **Purpose**: Active development and feature additions

### Upstream Repository
- **Remote**: `git@github.com:microsoft/sample-app-aoai-chatGPT.git`
- **Branch**: `upstream-sync` (tracks upstream/main)
- **Purpose**: Receive updates from Microsoft's original sample app

### Deployment Repository (Drupal Module)
- **Location**: `/Users/db2553/code/ai_engine/modules/ai_engine_chat/react/`
- **Remote**: Part of ai_engine Drupal module
- **Purpose**: Production deployment within Drupal 11 environment

## History

### Timeline
1. **February 2024**: ai_engine_chat Drupal module created with React component
2. **May 1, 2025**: Last significant React changes in ai_engine_chat (accessibility improvements)
3. **August 18, 2025**: ai_engine_chat/react copied into yale-development branch (commit 7fbdd32)
4. **August-December 2025**: 80+ commits of active development on yale-development
5. **December 18, 2025**: yale-development established as source of truth

### Key Differences
yale-development includes all ai_engine_chat changes PLUS:
- Enhanced error handling (NoPage.tsx for 404s)
- Improved styling architecture (CSS modules)
- Enhanced XSS protection (sanatizeAllowables.ts)
- Testing infrastructure (Jest, test framework)
- Development tooling (ESLint, Prettier)
- Image utilities (resizeImage.ts)
- Browser compatibility (polyfills.js)

## Development Workflow

### Primary Development
**Always develop in yale-development branch:**

```bash
cd /Users/db2553/code/askyale-aoai-chat-app
git checkout yale-development

# Make changes to frontend/
# Test changes
# Commit changes
git add .
git commit -m "feat: your feature description"
git push origin yale-development
```

### Syncing to Production (Drupal Module)

When ready to deploy changes to the Drupal module, use the sync script:

```bash
# From the yale-development repository
./scripts/sync-to-drupal.sh
```

Or manually:

```bash
rsync -av --delete \
  --exclude 'node_modules' \
  --exclude '.git' \
  --exclude 'dist' \
  frontend/ \
  /Users/db2553/code/ai_engine/modules/ai_engine_chat/react/

# Then commit in the ai_engine repository
cd /Users/db2553/code/ai_engine/modules/ai_engine_chat
git add react/
git commit -m "feat: sync from yale-development - [describe changes]"
git push
```

### Syncing from Upstream (Microsoft)

To pull in updates from the original Microsoft sample app:

```bash
# Fetch latest from upstream
git fetch upstream

# Update upstream-sync branch
git checkout upstream-sync
git merge upstream/main
git push origin upstream-sync

# Merge into yale-development (carefully review conflicts)
git checkout yale-development
git merge upstream-sync
# Resolve any conflicts
git push origin yale-development
```

## Important Notes

### DO NOT:
- ❌ Make changes directly in ai_engine_chat/react/
- ❌ Copy from ai_engine_chat to yale-development (yale-development is ahead)
- ❌ Skip testing before syncing to production

### DO:
- ✅ Always develop in yale-development
- ✅ Test changes thoroughly before syncing
- ✅ Document significant changes in commit messages
- ✅ Review changes in ai_engine after syncing
- ✅ Commit and push synced changes in the ai_engine repository

## File Structure Mapping

| yale-development | ai_engine_chat |
|------------------|----------------|
| `/frontend/src/` | `/react/src/` |
| `/frontend/package.json` | `/react/package.json` |
| `/frontend/vite.config.ts` | `/react/vite.config.ts` |
| `/frontend/index.html` | `/react/index.html` |

## Testing Before Sync

### In yale-development:
```bash
cd frontend
npm install
npm run dev       # Test locally
npm run build     # Ensure builds successfully
npm run test      # Run tests if available
```

### In ai_engine_chat (after sync):
```bash
cd /Users/db2553/code/ai_engine/modules/ai_engine_chat/react
npm install
npm run build
# Test within Drupal environment
```

## Troubleshooting

### If sync appears to lose changes:
1. Verify you're syncing FROM yale-development TO ai_engine_chat (not the reverse)
2. Check git status in both repositories
3. Review the diff before committing in ai_engine

### If upstream merge has conflicts:
1. Most conflicts will be in customized Yale-specific files
2. Prefer keeping Yale customizations over upstream defaults
3. Test thoroughly after resolving conflicts

### If production deployment fails:
1. Verify build succeeds in yale-development first
2. Check node_modules were excluded from sync
3. Run fresh npm install in ai_engine_chat after sync
4. Check Drupal module configuration

## Questions?

Contact the development team or refer to:
- Microsoft upstream docs: https://github.com/microsoft/sample-app-aoai-chatGPT
- This repository's issues: https://github.com/yalesites-org/askyale-aoai-chat-app/issues
