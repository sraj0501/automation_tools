"""
Admin Console FastAPI application — runs on ADMIN_PORT (default 8090).

Entry points:
    python -m backend.admin
    uvicorn backend.admin.app:app --port 8090
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.admin.routes import router, startup

app = FastAPI(
    title="DevTrack Admin Console",
    docs_url=None,    # no Swagger UI for admin — keep the attack surface small
    redoc_url=None,
)

# Mount static files
_STATIC_DIR = Path(__file__).parent / "static"
app.mount("/admin/static", StaticFiles(directory=str(_STATIC_DIR)), name="admin-static")

# Mount all admin routes under /admin
app.include_router(router, prefix="/admin")


@app.on_event("startup")
async def on_startup() -> None:
    startup()


def main() -> None:
    import uvicorn
    port = int(os.environ.get("ADMIN_PORT", "8090"))
    host = os.environ.get("ADMIN_HOST", "0.0.0.0")
    uvicorn.run("backend.admin.app:app", host=host, port=port, reload=False)
