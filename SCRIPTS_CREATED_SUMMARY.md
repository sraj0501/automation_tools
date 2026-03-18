# Azure DevOps Integration - Scripts & Diagnostics

## Summary

I've created two new scripts to help you fetch Azure DevOps work items and diagnosed the connectivity issue.

## 🔴 Current Issue

**Status: Authentication Failed (401 Unauthorized)**

Your Azure DevOps PAT (Personal Access Token) is either:
1. **Expired** (most likely - PATs expire after 1 year)
2. Missing required scopes (Work Items Read/Write, Project & Team Read)
3. Incorrect/corrupted value

## Created Scripts

### 1. `fetch_azure_simple.py` ⭐ START HERE
**Purpose**: Diagnostic script to test connectivity and identify issues  
**Type**: Synchronous (simple, easy to understand)  
**Best for**: Troubleshooting and quick testing

```bash
uv run python fetch_azure_simple.py
```

**Output**: Shows your configuration, connectivity status, and detailed error messages

### 2. `fetch_azure_workitems.py`
**Purpose**: Full-featured fetch tool for production use  
**Type**: Asynchronous (fast, handles large result sets)  
**Best for**: Integration into automated workflows

```bash
# Basic usage
uv run python fetch_azure_workitems.py

# With filtering
uv run python fetch_azure_workitems.py --state Active --type Bug --limit 20

# Verbose output
uv run python fetch_azure_workitems.py --verbose

# JSON output
uv run python fetch_azure_workitems.py --json
```

## 🔧 How to Fix the Issue

### Option 1: Generate a New PAT (Recommended)

1. **Go to token settings**:
   ```
   https://dev.azure.com/spglobal/_usersSettings/tokens
   ```

2. **Create a new token**:
   - Click **"+ New Token"**
   - Name: `devtrack`
   - Organization: `spglobal`
   - Expiration: 1 year
   - Scopes → Custom defined:
     - ✅ **Work Items** (Read & Write)
     - ✅ **Project & Team** (Read)
   - Click **Create**

3. **Copy the token** (shown only once!)

4. **Update `.env`**:
   ```bash
   AZURE_DEVOPS_PAT="your-new-token-here"
   ```

5. **Test the fix**:
   ```bash
   uv run python fetch_azure_simple.py
   ```

### Option 2: Check Existing Token

1. Go to: `https://dev.azure.com/spglobal/_usersSettings/tokens`
2. Find your current token and verify:
   - Not expired
   - Has correct scopes
   - Last used recently

## Files Created

```
/Users/sraj/git_apps/personal/automation_tools/
├── fetch_azure_simple.py              ← Synchronous diagnostic script
├── fetch_azure_workitems.py           ← Full-featured async script
├── test_azure_connectivity.py         ← First diagnostic attempt
├── AZURE_CONNECTIVITY_FIX.md          ← Detailed troubleshooting guide
└── SCRIPTS_CREATED_SUMMARY.md         ← This file
```

## Next Steps

1. **Regenerate your PAT token** (preferred solution)
2. **Update `.env` with new token**
3. **Test with**: `uv run python fetch_azure_simple.py`
4. **Use in production**: `uv run python fetch_azure_workitems.py`

## What Each Script Does

### `fetch_azure_simple.py`

**Checks (in order)**:
1. ✅ Environment variables loaded from `.env`
2. ✅ Required Python packages available
3. ✅ API authentication with Azure DevOps
4. ✅ Lists projects in your organization
5. ✅ Fetches work items assigned to you (if project set)
6. ✅ Displays work items in a table format

**Example output when working**:
```
✅ Authentication successful!
✅ Found 5 projects in organization
   - Ratings (ID: abc123...)
   - Platform (ID: def456...)
   ...

✅ Found 12 work items assigned to you

ID       Type         State        Title                                    Assigned To
-------- ------------ ------------ ---------------------------------------- ----------
  42     Bug          Active       Fix login page timeout error             John Doe
  43     Story        In Progress  Add dark mode support                    John Doe
  44     Task         New          Write API documentation                  John Doe
  ...

✅ Successfully fetched 3 of 12 work items
```

### `fetch_azure_workitems.py`

**Features**:
- **Async operations** for better performance
- **Filtering options**: `--state`, `--type`, `--limit`
- **Output formats**: Table (default) or `--json`
- **Verbose mode**: `--verbose` for detailed info
- **Error handling** with detailed error messages

## Backend Integration

Both scripts use the production Azure client from `backend/azure/client.py`:

```python
from backend.azure.client import AzureDevOpsClient

# The client expects environment variables:
# - AZURE_ORGANIZATION or ORGANIZATION
# - AZURE_PROJECT (optional, for project-scoped queries)
# - AZURE_DEVOPS_PAT or AZURE_API_KEY
```

## Troubleshooting

### "Missing AZURE_ORGANIZATION"
**Fix**: Add to `.env`:
```
AZURE_ORGANIZATION=spglobal
```

### "Missing AZURE_DEVOPS_PAT"
**Fix**: Add to `.env`:
```
AZURE_DEVOPS_PAT=your-token-here
```

### "Status 401 Unauthorized"
**Fix**: See "Option 1: Generate a New PAT" above

### "Status 403 Forbidden"
**Fix**: Token exists but lacks scopes. Regenerate with proper scopes.

### "Status 404 Not Found"
**Fix**: Check project name is correct in `.env`

### "Connection timeout"
**Fix**: Check internet connection and firewall

## Environment Variables Reference

Required:
```bash
AZURE_ORGANIZATION=spglobal          # or ORGANIZATION
AZURE_DEVOPS_PAT=token123...         # or AZURE_API_KEY
```

Optional:
```bash
AZURE_PROJECT=Ratings               # Required for work item queries
AZURE_API_VERSION=7.1               # Default is fine
```

## For Production Use

Once your PAT is working, integrate with the system:

1. **Python bridge automatically uses your credentials**:
   - `python_bridge.py` reads from `.env`
   - Syncs work items with local project manager

2. **Enable Azure sync** in `.env`:
   ```bash
   AZURE_SYNC_ENABLED=true
   AZURE_SYNC_AUTO_COMMENT=true
   ```

3. **Run the daemon**:
   ```bash
   devtrack start
   ```

## Questions?

- See `AZURE_CONNECTIVITY_FIX.md` for detailed troubleshooting
- Check `docs/AZURE_DEVOPS.md` for configuration details
- Review script comments for implementation details

---

**Last Updated**: March 18, 2026  
**Status**: ⚠️ Requires PAT regeneration
