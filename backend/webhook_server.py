"""
DevTrack Webhook Receiver

Lightweight FastAPI server for receiving webhook events from Azure DevOps,
GitHub, and Jira. Spawned by the Go daemon as a separate process.

Usage: python -m backend.webhook_server
"""

import asyncio
import base64
import hashlib
import hmac
import logging
import os
import signal
import sys

# Ensure project root is importable
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_script_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

try:
    from backend import config
    config._load_env()
except ImportError:
    config = None

from backend.webhook_handlers import WebhookEventHandler
from backend.webhook_notifier import WebhookNotifier

logger = logging.getLogger("devtrack.webhook_server")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="DevTrack Webhooks", version="1.0")

_handler: WebhookEventHandler | None = None


def _get_handler() -> WebhookEventHandler:
    global _handler
    if _handler is None:
        notifier = WebhookNotifier()
        _handler = WebhookEventHandler(ipc_client=None, notifier=notifier)
    return _handler


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _cfg(key: str, default: str = "") -> str:
    if config:
        return config.get(key, default)
    return os.getenv(key, default)


def _cfg_bool(key: str, default: bool = False) -> bool:
    if config:
        return config.get_bool(key, default)
    val = os.getenv(key, "").lower().strip()
    return val in ("true", "1", "yes", "on") if val else default


async def _verify_azure_basic_auth(request: Request) -> None:
    """Validate HTTP Basic Auth for Azure DevOps service hooks."""
    expected_user = _cfg("WEBHOOK_AZURE_USERNAME", "")
    expected_pass = _cfg("WEBHOOK_AZURE_PASSWORD", "")
    if not expected_user and not expected_pass:
        # Auth not configured — allow all (dev mode)
        return

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Basic "):
        raise HTTPException(status_code=401, detail="Missing Basic auth")

    try:
        decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
        username, password = decoded.split(":", 1)
    except Exception:
        raise HTTPException(status_code=401, detail="Malformed auth header")

    if username != expected_user or password != expected_pass:
        raise HTTPException(status_code=403, detail="Invalid credentials")


async def _verify_github_signature(request: Request) -> None:
    """Validate HMAC-SHA256 signature for GitHub webhooks."""
    secret = _cfg("WEBHOOK_GITHUB_SECRET", "")
    if not secret:
        return  # Signature validation not configured

    signature_header = request.headers.get("X-Hub-Signature-256", "")
    if not signature_header.startswith("sha256="):
        raise HTTPException(status_code=401, detail="Missing GitHub signature")

    body = await request.body()
    expected = "sha256=" + hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature_header, expected):
        raise HTTPException(status_code=403, detail="Invalid signature")


async def _verify_gitlab_token(request: Request) -> None:
    """Validate GitLab webhook secret token."""
    secret = _cfg("WEBHOOK_GITLAB_SECRET")
    if not secret:
        return  # No secret configured — allow all (dev mode)
    token = request.headers.get("X-Gitlab-Token", "")
    if token != secret:
        raise HTTPException(status_code=401, detail="Invalid GitLab token")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/webhooks/azure-devops")
async def handle_azure_devops_webhook(
    request: Request,
    _auth: None = Depends(_verify_azure_basic_auth),
) -> JSONResponse:
    """Handle Azure DevOps service hook events."""
    handler = _get_handler()
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    event_type = body.get("eventType", "")
    resource = body.get("resource", {})

    if not event_type:
        raise HTTPException(status_code=400, detail="Missing eventType")

    result = await handler.handle_azure_event(event_type, resource, body)
    return JSONResponse(content=result)


@app.post("/webhooks/github")
async def handle_github_webhook(
    request: Request,
    _auth: None = Depends(_verify_github_signature),
) -> JSONResponse:
    """Handle GitHub webhook events (placeholder)."""
    handler = _get_handler()
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    event_type = request.headers.get("X-GitHub-Event", "unknown")
    result = await handler.handle_github_event(event_type, body)
    return JSONResponse(content=result)


@app.post("/webhooks/gitlab")
async def handle_gitlab_webhook(
    request: Request,
    _auth: None = Depends(_verify_gitlab_token),
) -> JSONResponse:
    """Handle GitLab webhook events (issue events, MR events, comments)."""
    handler = _get_handler()
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    event_type = request.headers.get("X-Gitlab-Event", "unknown")
    result = await handler.handle_gitlab_event(event_type, body)
    return JSONResponse(content=result)


@app.post("/webhooks/jira")
async def handle_jira_webhook(request: Request) -> JSONResponse:
    """Handle Jira webhook events (placeholder)."""
    handler = _get_handler()
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    event_type = body.get("webhookEvent", "unknown")
    result = await handler.handle_jira_event(event_type, body)
    return JSONResponse(content=result)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "devtrack-webhooks"}


@app.get("/status")
async def status() -> dict:
    return {
        "service": "devtrack-webhooks",
        "azure_devops": _cfg_bool("AZURE_SYNC_ENABLED"),
        "webhook_enabled": _cfg_bool("WEBHOOK_ENABLED"),
        "notify_os": _cfg_bool("WEBHOOK_NOTIFY_OS", True),
        "notify_terminal": _cfg_bool("WEBHOOK_NOTIFY_TERMINAL", True),
    }


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

async def _connect_ipc() -> None:
    """Attempt to connect to Go daemon IPC on startup."""
    global _handler
    try:
        from backend.ipc_client import IPCClient
        host = _cfg("IPC_HOST", "127.0.0.1")
        port = int(_cfg("IPC_PORT", "35893"))
        client = IPCClient(host, port)
        client.connect()
        handler = _get_handler()
        handler.ipc_client = client
        logger.info(f"Connected to IPC server at {host}:{port}")
    except Exception as e:
        logger.warning(f"Could not connect to IPC server: {e} (running standalone)")


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("DevTrack Webhook Server starting")
    await _connect_ipc()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    handler = _get_handler()
    if handler.ipc_client:
        try:
            handler.ipc_client.close()
        except Exception:
            pass
    logger.info("DevTrack Webhook Server stopped")


def main() -> None:
    """Entry point when run as a module."""
    import uvicorn

    host = _cfg("WEBHOOK_HOST", "0.0.0.0")
    port = int(_cfg("WEBHOOK_PORT", "8089"))

    logger.info(f"Starting webhook server on {host}:{port}")
    uvicorn.run(
        "backend.webhook_server:app",
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
