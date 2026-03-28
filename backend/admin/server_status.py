"""
Server status — aggregates process info and health checks for the admin dashboard.
Bridges server_tui.process_monitor and server_tui.health_client.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ProcessStatus:
    name: str
    running: bool
    pid: Optional[int]
    cpu_percent: float
    mem_mb: float
    status: str


@dataclass
class ServiceStatus:
    name: str
    url: str
    ok: bool
    detail: str


@dataclass
class ServerSnapshot:
    processes: list[ProcessStatus]
    services: list[ServiceStatus]
    llm_provider: str
    llm_model: str
    webhook_port: int
    admin_port: int


def get_snapshot() -> ServerSnapshot:
    processes: list[ProcessStatus] = []
    services: list[ServiceStatus] = []

    try:
        from backend.server_tui.process_monitor import ProcessMonitor
        mon = ProcessMonitor()
        mon.refresh()
        for p in mon.processes:
            processes.append(ProcessStatus(
                name=p.name,
                running=p.running,
                pid=p.pid,
                cpu_percent=p.cpu_percent,
                mem_mb=p.mem_mb,
                status=p.status,
            ))
    except Exception:
        pass

    try:
        from backend.server_tui.health_client import check_all
        for h in check_all():
            services.append(ServiceStatus(
                name=h.name, url=h.url, ok=h.ok, detail=h.detail
            ))
    except Exception:
        pass

    return ServerSnapshot(
        processes=processes,
        services=services,
        llm_provider=os.environ.get("LLM_PROVIDER", "—"),
        llm_model=os.environ.get("OLLAMA_MODEL") or os.environ.get("OPENAI_MODEL") or "—",
        webhook_port=int(os.environ.get("WEBHOOK_PORT", "8089")),
        admin_port=int(os.environ.get("ADMIN_PORT", "8090")),
    )
