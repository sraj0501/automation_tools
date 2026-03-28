"""
Admin Console FastAPI router — mounted at /admin in the admin app.

All routes require a valid session cookie (see auth.py).
Process control actions delegate to server_tui.process_monitor.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from backend.admin.auth import (
    COOKIE_NAME,
    check_credentials,
    create_token,
    decode_token,
    require_auth,
)
from backend.admin.server_status import get_snapshot
from backend.admin.user_manager import (
    create_api_key,
    create_user,
    delete_user,
    ensure_default_admin,
    get_audit_log,
    get_user,
    init_db,
    list_api_keys,
    list_users,
    log_action,
    revoke_api_key,
    touch_last_login,
)

router = APIRouter()

_TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


# ---------------------------------------------------------------------------
# Startup initialisation (called from app.py)
# ---------------------------------------------------------------------------

def startup() -> None:
    init_db()
    admin_user = os.environ.get("ADMIN_USERNAME", "admin")
    admin_pass = os.environ.get("ADMIN_PASSWORD", "")
    if admin_pass:
        ensure_default_admin(admin_user, admin_pass)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ctx(request: Request, current_user: str, active: str, **extra) -> dict:
    return {"request": request, "current_user": current_user, "active": active, **extra}


def _snapshot_ctx():
    """Return a fresh server snapshot (non-blocking; errors are silenced)."""
    try:
        return get_snapshot()
    except Exception:
        from backend.admin.server_status import ServerSnapshot
        return ServerSnapshot(processes=[], services=[], llm_provider="—",
                              llm_model="—", webhook_port=8089, admin_port=8090)


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
async def login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
):
    if not check_credentials(username, password):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password"},
            status_code=401,
        )
    touch_last_login(username)
    log_action(username, "login", ip=request.client.host if request.client else "")
    token = create_token(username)
    resp = RedirectResponse("/admin/", status_code=303)
    resp.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", max_age=8 * 3600)
    return resp


@router.get("/logout")
async def logout(current_user: str = Depends(require_auth)):
    resp = RedirectResponse("/admin/login", status_code=303)
    resp.delete_cookie(COOKIE_NAME)
    return resp


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, current_user: str = Depends(require_auth)):
    snapshot = _snapshot_ctx()
    user_count = len(list_users())
    return templates.TemplateResponse(
        "dashboard.html",
        _ctx(request, current_user, "dashboard", snapshot=snapshot, user_count=user_count),
    )


# ---------------------------------------------------------------------------
# HTMX partials
# ---------------------------------------------------------------------------

@router.get("/_partials/processes", response_class=HTMLResponse)
async def partial_processes(request: Request, current_user: str = Depends(require_auth)):
    snapshot = _snapshot_ctx()
    return templates.TemplateResponse(
        "_proc_rows.html",
        {"request": request, "snapshot": snapshot},
    )


# ---------------------------------------------------------------------------
# Process control (HTMX POST — returns updated proc rows)
# ---------------------------------------------------------------------------

@router.post("/process/{name}/restart", response_class=HTMLResponse)
async def process_restart(
    name: str, request: Request, current_user: str = Depends(require_auth)
):
    try:
        from backend.server_tui.process_monitor import ProcessMonitor
        mon = ProcessMonitor()
        mon.restart(name)
        log_action(current_user, "restart_process", name,
                   ip=request.client.host if request.client else "")
    except Exception:
        pass
    snapshot = _snapshot_ctx()
    return templates.TemplateResponse("_proc_rows.html", {"request": request, "snapshot": snapshot})


@router.post("/process/{name}/stop", response_class=HTMLResponse)
async def process_stop(
    name: str, request: Request, current_user: str = Depends(require_auth)
):
    try:
        from backend.server_tui.process_monitor import ProcessMonitor
        mon = ProcessMonitor()
        mon.stop(name)
        log_action(current_user, "stop_process", name,
                   ip=request.client.host if request.client else "")
    except Exception:
        pass
    snapshot = _snapshot_ctx()
    return templates.TemplateResponse("_proc_rows.html", {"request": request, "snapshot": snapshot})


@router.post("/process/{name}/start", response_class=HTMLResponse)
async def process_start(
    name: str, request: Request, current_user: str = Depends(require_auth)
):
    try:
        from backend.server_tui.process_monitor import ProcessMonitor
        mon = ProcessMonitor()
        mon.restart(name)  # restart handles start of stopped process
        log_action(current_user, "start_process", name,
                   ip=request.client.host if request.client else "")
    except Exception:
        pass
    snapshot = _snapshot_ctx()
    return templates.TemplateResponse("_proc_rows.html", {"request": request, "snapshot": snapshot})


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@router.get("/users", response_class=HTMLResponse)
async def users_page(
    request: Request,
    current_user: str = Depends(require_auth),
    flash: Optional[str] = None,
    flash_type: str = "info",
):
    users = list_users()
    return templates.TemplateResponse(
        "users.html",
        _ctx(request, current_user, "users", users=users, flash=flash, flash_type=flash_type),
    )


@router.post("/users/create")
async def users_create(
    request: Request,
    current_user: str = Depends(require_auth),
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form("viewer"),
):
    if get_user(username):
        return RedirectResponse(
            f"/admin/users?flash=User+'{username}'+already+exists&flash_type=error",
            status_code=303,
        )
    create_user(username, password, role)
    log_action(current_user, "create_user", f"username={username} role={role}",
               ip=request.client.host if request.client else "")
    return RedirectResponse(f"/admin/users?flash=User+'{username}'+created", status_code=303)


@router.post("/users/{username}/delete")
async def users_delete(
    username: str, request: Request, current_user: str = Depends(require_auth)
):
    if username == current_user:
        return RedirectResponse(
            "/admin/users?flash=Cannot+delete+yourself&flash_type=error", status_code=303
        )
    delete_user(username)
    log_action(current_user, "delete_user", f"username={username}",
               ip=request.client.host if request.client else "")
    return RedirectResponse(f"/admin/users?flash=User+'{username}'+deleted", status_code=303)


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------

@router.get("/users/{username}/keys", response_class=HTMLResponse)
async def api_keys_page(
    username: str, request: Request, current_user: str = Depends(require_auth),
    new_key: Optional[str] = None,
):
    api_keys = list_api_keys(username)
    return templates.TemplateResponse(
        "api_keys.html",
        _ctx(request, current_user, "users", target_user=username,
             api_keys=api_keys, new_key=new_key),
    )


@router.post("/users/{username}/keys/create")
async def api_keys_create(
    username: str,
    request: Request,
    current_user: str = Depends(require_auth),
    label: str = Form(""),
):
    raw, _ = create_api_key(username, label)
    log_action(current_user, "create_api_key", f"user={username} label={label}",
               ip=request.client.host if request.client else "")
    # Pass the raw key as a query param so it can be shown once
    from urllib.parse import quote
    return RedirectResponse(
        f"/admin/users/{username}/keys?new_key={quote(raw)}", status_code=303
    )


@router.post("/keys/{key_id}/revoke")
async def api_key_revoke(
    key_id: int, request: Request, current_user: str = Depends(require_auth)
):
    revoke_api_key(key_id)
    log_action(current_user, "revoke_api_key", f"key_id={key_id}",
               ip=request.client.host if request.client else "")
    # Redirect back to the referring user's key page (best-effort)
    referer = request.headers.get("referer", "/admin/users")
    return RedirectResponse(referer, status_code=303)


# ---------------------------------------------------------------------------
# Server config page
# ---------------------------------------------------------------------------

@router.get("/server", response_class=HTMLResponse)
async def server_page(request: Request, current_user: str = Depends(require_auth)):
    snapshot = _snapshot_ctx()
    config = {
        "LLM_PROVIDER":  os.environ.get("LLM_PROVIDER", "—"),
        "OLLAMA_HOST":   os.environ.get("OLLAMA_HOST", "—"),
        "OLLAMA_MODEL":  os.environ.get("OLLAMA_MODEL", "—"),
        "OPENAI_MODEL":  os.environ.get("OPENAI_MODEL", "—"),
        "ANTHROPIC_MODEL": os.environ.get("ANTHROPIC_MODEL", "—"),
        "GROQ_MODEL":    os.environ.get("GROQ_MODEL", "—"),
    }
    integrations = {
        "Azure DevOps": "configured" if os.environ.get("AZURE_DEVOPS_PAT") else "not set",
        "GitHub":       "configured" if os.environ.get("GITHUB_TOKEN") else "not set",
        "GitLab":       "configured" if os.environ.get("GITLAB_PAT") else "not set",
        "Jira":         "configured" if os.environ.get("JIRA_API_TOKEN") else "not set",
        "Telegram":     "configured" if os.environ.get("TELEGRAM_BOT_TOKEN") else "not set",
        "MS Graph":     "configured" if os.environ.get("AZURE_DEVOPS_PAT") else "not set",
    }
    return templates.TemplateResponse(
        "server.html",
        _ctx(request, current_user, "server",
             snapshot=snapshot, config=config, integrations=integrations),
    )


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

@router.get("/audit", response_class=HTMLResponse)
async def audit_page(request: Request, current_user: str = Depends(require_auth)):
    entries = get_audit_log(limit=200)
    return templates.TemplateResponse(
        "audit.html",
        _ctx(request, current_user, "audit", entries=entries),
    )
