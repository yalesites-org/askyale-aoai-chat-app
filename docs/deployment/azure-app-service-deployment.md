# Azure App Service Deployment from GitHub

This document captures the steps to deploy this app from a GitHub repository to an existing Azure App Service instance, including what worked, what failed, and why.

Tested: March 2026 on `beaconcs3254` (resource group: `subscription-ai-eastus2-rg`).

---

## Prerequisites

- Azure CLI installed and authenticated (`az login`)
- The target app already exists in Azure App Service
- The GitHub repository is public

---

## Step 1: Check the existing deployment source

Before making changes, check what deployment source is currently configured:

```bash
az webapp deployment source show \
  --name <app-name> \
  --resource-group <resource-group> \
  --output json
```

**Result:** Returns the current `repoUrl`, `branch`, `isManualIntegration`, and whether a Docker image (`linuxFxVersion`) is in use.

---

## Step 2: Check if the app is using a Docker image

This is critical. If the app is running from a Docker image, GitHub source deployment will put files in `/home/site/wwwroot/` but the container will continue running from its baked-in image -- your code changes will have no effect.

```bash
az webapp config show \
  --name <app-name> \
  --resource-group <resource-group> \
  --query "linuxFxVersion"
```

**If the result looks like `"DOCKER|registry.azurecr.io/image:tag"`:** The app is running from a Docker image. See Step 3A.

**If the result looks like `"PYTHON|3.11"`:** The app is using the built-in Python runtime. Skip to Step 3B.

---

## Step 3A: Switch from Docker to built-in Python runtime (if applicable)

If you want to deploy directly from GitHub source (not Docker), you must switch the runtime. This is a significant change from a Docker-based deployment.

```bash
# Switch to built-in Python 3.11 runtime
az webapp config set \
  --name <app-name> \
  --resource-group <resource-group> \
  --linux-fx-version "PYTHON|3.11"

# Set the startup command
az webapp config set \
  --name <app-name> \
  --resource-group <resource-group> \
  --startup-file "gunicorn app:app -w 3 -k uvicorn.workers.UvicornWorker"
```

**Note:** Do NOT use `python -m gunicorn ...` -- Azure's built-in runtime uses its own virtualenv path and `python -m` won't work correctly.

**Worked:** Yes, after also enabling the build step in Step 4.

---

## Step 3B: Disconnect existing deployment source

If a deployment source is already configured (any type), you must disconnect it before configuring a new one. Skipping this causes a `Conflict with existing ScmType` error.

```bash
az webapp deployment source delete \
  --name <app-name> \
  --resource-group <resource-group>
```

**Worked:** Yes.

---

## Step 4: Enable build during deployment

This tells Azure's Oryx build system to install Python dependencies from `requirements.txt` when deploying. Without this, the app will fail to start with `ModuleNotFoundError` (e.g., `No module named 'uvicorn'`).

```bash
az webapp config appsettings set \
  --name <app-name> \
  --resource-group <resource-group> \
  --settings SCM_DO_BUILD_DURING_DEPLOYMENT="true"
```

**Verify it was set:**

```bash
az webapp config appsettings list \
  --name <app-name> \
  --resource-group <resource-group> \
  --query "[?name=='SCM_DO_BUILD_DURING_DEPLOYMENT']"
```

Check that `"value": "true"` is shown (not `null`).

**Worked:** Yes. Required for the app to start correctly.

**Important:** When scripting these steps, restart the app (`az webapp restart`) after setting this value and before triggering a deployment sync. Without a restart, Kudu may not pick up the new setting in time, causing the Oryx build to be skipped and dependencies not installed.

---

## Step 5: Configure GitHub as the deployment source

For a **public repository**, use `--manual-integration` to skip the GitHub token/webhook requirement:

```bash
az webapp deployment source config \
  --name <app-name> \
  --resource-group <resource-group> \
  --repo-url https://github.com/<org>/<repo> \
  --branch <branch-name> \
  --manual-integration
```

**Note:** `--manual-integration` means deployments are NOT automatic on push. You must manually trigger a sync each time (see Step 6).

**Without `--manual-integration`:** Azure requires a GitHub personal access token (PAT) even for public repos, which returns `Cannot find SourceControlToken with name GitHub`. The `--manual-integration` flag bypasses this.

**Worked:** Yes.

---

## Step 6: Trigger deployment

Since `--manual-integration` is used, deployments must be triggered manually:

```bash
az webapp deployment source sync \
  --name <app-name> \
  --resource-group <resource-group>
```

Run this after every push to the branch when you want the changes deployed.

**Worked:** Yes.

---

## Step 7: Verify the correct commit is deployed

Check deployment history to confirm the right commit is active:

```bash
az webapp log deployment list \
  --name <app-name> \
  --resource-group <resource-group> \
  --output table
```

Look for your commit message and the `Active: True` row. The URL column contains the full commit SHA.

Compare with local:

```bash
git rev-parse HEAD
```

**Worked:** Yes.

---

## Step 8: Tail logs

```bash
az webapp log tail \
  --name <app-name> \
  --resource-group <resource-group>
```

The message `No new trace in the past 1 min(s)` is normal -- it just means the app is idle. The log stream remains open waiting for new output.

To see application-level logs (e.g., `logging.info()` calls), enable verbose logging:

```bash
az webapp log config \
  --name <app-name> \
  --resource-group <resource-group> \
  --level verbose \
  --application-logging filesystem
```

**Worked:** Yes, though INFO-level app logs may not appear without this setting.

---

## Step 9: Set environment variables

Environment variables are set as Application Settings in Azure App Service. The `.env` file is not used in production -- all config must be in App Settings.

```bash
az webapp config appsettings set \
  --name <app-name> \
  --resource-group <resource-group> \
  --settings \
    KEY1=value1 \
    KEY2=value2
```

Verify:

```bash
az webapp config appsettings list \
  --name <app-name> \
  --resource-group <resource-group> \
  --output table
```

**Worked:** Yes.

---

## Confirming the app is running from GitHub source

When the app is using the built-in Python runtime and deployed from GitHub, the log paths in startup output will reference `/home/site/wwwroot/backend/...`. If you still see `/usr/src/app/backend/...` in the logs, the app is still running from the old Docker image.

---

## Common Errors and Fixes

| Error | Cause | Fix |
|---|---|---|
| `Cannot find SourceControlToken with name GitHub` | Azure requires a GitHub token for webhook setup | Add `--manual-integration` flag |
| `Conflict with existing ScmType: ExternalGit` | A deployment source is already configured | Run `az webapp deployment source delete` first |
| `ModuleNotFoundError: No module named 'uvicorn'` | Oryx build didn't install dependencies | Set `SCM_DO_BUILD_DURING_DEPLOYMENT="true"` |
| Code changes have no effect after deployment | App is running from a Docker image, not GitHub source | Check `linuxFxVersion`; switch to `PYTHON|3.11` if needed |
| `'list' is misspelled or not recognized` | `az webapp deployment list` does not exist | Use `az webapp log deployment list` instead |
| `az webapp ssh` returns "SSH is not enabled" | SSH not enabled on the App Service plan/tier | Use Kudu console at `https://<app>.scm.azurewebsites.net/DebugConsole` |

---

## Kudu Console

The Kudu debug console is accessible at:

```
https://<app-name>.scm.azurewebsites.net/DebugConsole
```

Note: The Kudu SSH shell uses the system Python, not the app's virtualenv. Running Python scripts from there requires finding and using the virtualenv's Python binary. For the built-in Python runtime, this is generally not practical -- use log tailing instead to diagnose runtime issues.

---

## Full Command Reference (in order)

```bash
# 1. Check current deployment source
az webapp deployment source show --name <app> --resource-group <rg> --output json

# 2. Check if running from Docker image
az webapp config show --name <app> --resource-group <rg> --query "linuxFxVersion"

# 3. Switch from Docker to built-in Python (only if needed)
az webapp config set --name <app> --resource-group <rg> --linux-fx-version "PYTHON|3.11"
az webapp config set --name <app> --resource-group <rg> --startup-file "gunicorn app:app -w 3 -k uvicorn.workers.UvicornWorker"

# 4. Disconnect existing deployment source
az webapp deployment source delete --name <app> --resource-group <rg>

# 5. Enable build during deployment
az webapp config appsettings set --name <app> --resource-group <rg> --settings SCM_DO_BUILD_DURING_DEPLOYMENT="true"

# 6. Configure GitHub source
az webapp deployment source config --name <app> --resource-group <rg> \
  --repo-url https://github.com/<org>/<repo> --branch <branch> --manual-integration

# 7. Trigger deployment
az webapp deployment source sync --name <app> --resource-group <rg>

# 8. Verify deployed commit
az webapp log deployment list --name <app> --resource-group <rg> --output table

# 9. Tail logs
az webapp log tail --name <app> --resource-group <rg>

# 10. Set environment variables
az webapp config appsettings set --name <app> --resource-group <rg> --settings KEY=value
```
