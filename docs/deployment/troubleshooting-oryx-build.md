# Troubleshooting: Oryx Build Not Running on Azure App Service

Documented during deployment of `beaconprompt` (resource group: `subscription-ai-eastus2-rg`), March 2026.

---

## Symptom

After running `deploy-github-source.sh`, the app crashes in a loop with:

```
WARNING: Could not find virtual environment directory /home/site/wwwroot/antenv.
WARNING: Could not find package directory /home/site/wwwroot/__oryx_packages__.
Error: class uri 'uvicorn.workers.UvicornWorker' invalid or not found:
ModuleNotFoundError: No module named 'uvicorn'
```

The startup command is correct (`gunicorn app:app -w 3 -k uvicorn.workers.UvicornWorker`), but no dependencies were installed because the Oryx BUILD phase never ran. The runtime Oryx (startup script creation) runs, but it can't find a virtualenv.

---

## Root Causes Found

### 1. `deployment source config` already triggers an initial fetch/build

`az webapp deployment source config` triggers an initial git fetch and Oryx build automatically. The script was then calling `az webapp deployment source sync` immediately after, which queued a SECOND fetch before the first one finished. This caused conflicts and stalled deployments.

**Fix:** Removed the explicit sync from the script. The `source config` command handles the initial deployment.

### 2. Large repo fetch can hang or time out

The repo is ~98MB. Kudu's git fetch from GitHub can take several minutes or hang entirely for repos this size. When the fetch hangs or times out:

- `branch` in the deployment source config ends up as `null`
- No deployment record is created in Kudu (`/api/deployments` returns `[]`)
- The Oryx build never triggers

**How to detect:** Run `az webapp deployment source show` and check if `branch` is `null`. Also check `az webapp log deployment list` -- if it returns `[]`, no deployment was ever processed.

**Fix:** Added branch verification after `source config` in the script. If the branch is `null`, the script exits with an error instead of silently proceeding.

### 3. Restarting the app during deployment disrupts Kudu

Adding `az webapp restart` between setting app settings and configuring the source caused Kudu's SCM container to restart, which stopped in-progress deployments with:

> "Deployment has been stopped due to SCM container restart. Do not perform a management operation and a deployment operation in quick succession."

**Fix:** Removed the restart from the script entirely.

### 4. Container starts before build completes

Even when the Oryx build runs successfully, the app container may have already started (and be crash-looping) from before the build finished. The running container doesn't automatically pick up the newly created virtualenv.

**Fix:** Restart the app AFTER the build completes:

```bash
az webapp restart --name <app> --resource-group <rg>
```

---

## Diagnostic Commands

```bash
# Check if branch is set (null = fetch failed)
az webapp deployment source show \
  --name <app> --resource-group <rg> \
  --query "{branch: branch, repoUrl: repoUrl}" --output json

# Check if any deployments were recorded ([] = none)
az webapp log deployment list \
  --name <app> --resource-group <rg> --output table

# Check deployment log details for a specific deployment
az webapp log deployment show \
  --name <app> --resource-group <rg> \
  --deployment-id <id> --output json

# Check build setting is present
az webapp config appsettings list \
  --name <app> --resource-group <rg> \
  --query "[?name=='SCM_DO_BUILD_DURING_DEPLOYMENT']"

# Check runtime
az webapp config show \
  --name <app> --resource-group <rg> \
  --query "linuxFxVersion" --output tsv

# Kudu deployments API (browser)
https://<app>.scm.azurewebsites.net/api/deployments
```

---

## Current State of `beaconprompt` (as of 2026-03-16)

- Runtime: `PYTHON|3.11`
- Startup command: `gunicorn app:app -w 3 -k uvicorn.workers.UvicornWorker`
- `SCM_DO_BUILD_DURING_DEPLOYMENT`: `true`
- Source: External Git, `https://github.com/yalesites-org/askyale-aoai-chat-app`, branch `feat/portkey`
- Oryx build: Ran successfully (user confirmed it was extracting nodejs and python)
- **Next step:** Restart the app so the container picks up the virtualenv created by the build:
  ```bash
  az webapp restart --name beaconprompt --resource-group subscription-ai-eastus2-rg
  ```
- After restart, check logs to confirm `WARNING: Could not find virtual environment directory` is gone

---

## Script Changes Made

### `scripts/deploy-github-source.sh`

1. **Removed** `az webapp restart` between Steps 5 and 6 (was disrupting Kudu)
2. **Removed** explicit `az webapp deployment source sync` (Step 7) -- `source config` already triggers initial deployment
3. **Added** branch verification after `source config` -- exits with error if branch is `null` (fetch timed out)
4. **Added** deployment polling loop (Step 7) -- polls every 10s for up to 5 minutes waiting for deployment to complete
5. **Added** note that Step 6 can take several minutes for large repos

### `docs/deployment/azure-app-service-deployment.md`

Added note after Step 4 about restarting the app when scripting these steps.

---

## Comparison: Working vs Non-Working Instance

| | beaconcommencement (working) | beaconprompt (broken initially) |
|---|---|---|
| `/api/deployments` | Has entries, active deployment from Mar 10 | Empty `[]` (no deployments recorded) |
| `branch` in source config | `feat/portkey` | `null` (fetch failed/timed out) |
| Oryx build | Ran during initial manual setup | Never triggered until manual reconfiguration |
| Setup method | Manual CLI commands (natural delays) | Script (commands back-to-back) |
