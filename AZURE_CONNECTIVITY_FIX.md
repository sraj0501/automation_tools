# Azure DevOps Connectivity Issue - Diagnostic Report

**Date**: March 18, 2026  
**Status**: ❌ **Authentication Failed (401 Unauthorized)**

## Problem Summary

When attempting to connect to Azure DevOps using the stored PAT (Personal Access Token), the API returns a **401 Unauthorized** response. This prevents work items from being fetched.

### Error Details

```
Status Code: 401 Unauthorized
Organization: spglobal
Project: Ratings
```

## Root Causes (in order of likelihood)

1. **PAT Token is Expired** ⚠️ (Most Likely)
   - Azure DevOps PAT tokens have expiration dates
   - After expiration, they become invalid automatically
   - Typical validity: 1 year from creation

2. **PAT Token Lacks Required Scopes**
   - The token may have been created with insufficient permissions
   - Required scopes:
     - **Work Items**: Read & Write
     - **Project & Team**: Read

3. **PAT Token is Malformed or Incorrect**
   - The stored value in `.env` may be corrupted
   - May have been partially copied during setup

## Solution Steps

### Step 1: Check PAT Status

Go to Azure DevOps token management:
```
https://dev.azure.com/spglobal/_usersSettings/tokens
```

1. Open the link above in your browser
2. Look for your PAT token and check:
   - **Expiration Date**: Is it in the past?
   - **Last Used**: When was it last used?
   - **Scopes**: Does it have "Work Items" and "Project & Team"?

### Step 2: Generate a New PAT Token

If the token is expired or missing scopes:

1. Go to: `https://dev.azure.com/spglobal/_usersSettings/tokens`
2. Click **"+ New Token"** button
3. Fill in the form:
   - **Name**: `devtrack` (or any identifier you prefer)
   - **Organization**: Select `spglobal`
   - **Expiration**: Set to 1 year (or maximum available)
   - **Scopes**: Select **Custom defined**
     - ✅ Work Items (Read & Write)
     - ✅ Project & Team (Read)
4. Click **Create**
5. **Copy the token value immediately** (it will only be shown once!)

### Step 3: Update .env File

1. Open `.env` in your editor
2. Find the line:
   ```
   AZURE_DEVOPS_PAT="your-azure-devops-pat-here"
   ```
3. Replace with the new token:
   ```
   AZURE_DEVOPS_PAT="<paste-your-new-token-here>"
   ```
4. Save the file
5. **Do not commit this to git!** (Keep `.env` in `.gitignore`)

### Step 4: Verify the Fix

Run the connectivity test again:

```bash
uv run python fetch_azure_simple.py
```

Expected output if successful:
```
✅ Authentication successful!
✅ Found N projects in organization
```

## Alternative: Using Config Functions

If you prefer, you can also use the backend config functions directly. The system responds to these environment variable names:

- `AZURE_DEVOPS_PAT` (preferred)
- `AZURE_API_KEY` (legacy fallback)
- `ORGANIZATION` (fallback for AZURE_ORGANIZATION)
- `PROJECT` (fallback for AZURE_PROJECT)

## Scripts to Use

Two scripts are available to fetch Azure DevOps work items:

### 1. `fetch_azure_simple.py` (Recommended for testing)
- Synchronous (non-async)
- Simple, easy to understand
- Good for debugging connectivity issues
- Shows detailed diagnostics

```bash
uv run python fetch_azure_simple.py
```

### 2. `fetch_azure_workitems.py` (Full-featured)
- Asynchronous for better performance
- More command-line options (filtering, JSON output, etc.)
- Better for production use

```bash
# Basic usage
uv run python fetch_azure_workitems.py

# Filter by state
uv run python fetch_azure_workitems.py --state Active --type Bug

# Show details
uv run python fetch_azure_workitems.py --verbose

# JSON output
uv run python fetch_azure_workitems.py --json
```

## Common Issues and Solutions

### Issue: "Missing Configuration"
**Solution**: Verify all required environment variables are set:
```bash
grep -E "AZURE_ORGANIZATION|AZURE_DEVOPS_PAT|AZURE_PROJECT" .env
```

### Issue: "Connection Timeout"
**Solution**: 
- Check your internet connection
- Verify firewall isn't blocking `dev.azure.com`
- Check if Azure DevOps is experiencing an outage

### Issue: "403 Forbidden"
**Solution**:
- The PAT may lack required scopes
- Regenerate the PAT with proper scopes (see Step 2 above)
- Ensure the organization name is correct

### Issue: "404 Not Found"
**Solution**:
- The project name may be incorrect
- Verify `AZURE_PROJECT` matches exactly (case-sensitive)
- Use `fetch_azure_workitems.py` to list available projects

## Next Steps After Fixing

Once the connectivity is working:

1. **Test with a specific project**:
   ```bash
   uv run python fetch_azure_workitems.py --limit 5
   ```

2. **Integrate with the daemon**:
   The Python bridge will automatically use your credentials from `.env`

3. **Set up Azure sync** (optional):
   Configure these in `.env` for bidirectional sync:
   ```
   AZURE_SYNC_ENABLED=true
   AZURE_SYNC_AUTO_COMMENT=true
   AZURE_SYNC_AUTO_TRANSITION=false
   ```

4. **Check the async client**:
   The main system uses `backend/azure/client.py` which provides:
   - `AzureDevOpsClient` class
   - Methods: `get_my_work_items()`, `get_work_item()`, `search_work_items()`
   - Updates: `add_comment()`, `update_work_item()`

## Testing the Backend Client

You can also test the async client directly:

```bash
uv run python << 'EOF'
import asyncio
from backend.azure.client import AzureDevOpsClient

async def test():
    client = AzureDevOpsClient()
    if not client.is_configured():
        print("ERROR: Not configured")
        return
    
    items = await client.get_my_work_items(max_results=5)
    for item in items:
        print(f"#{item.id}: {item.title} ({item.state})")
    
    await client.close()

asyncio.run(test())
EOF
```

## Documentation References

- [Azure DevOps REST API](https://learn.microsoft.com/en-us/rest/api/azure/devops/)
- [PAT Token Management](https://learn.microsoft.com/en-us/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate)
- [Work Item Query Language (WIQL)](https://learn.microsoft.com/en-us/azure/devops/boards/queries/wiql/syntax)

---

**Questions or Issues?** Check `KNOWN_ISSUES.md` or run the diagnostic script again with `--verbose` flag if available.
