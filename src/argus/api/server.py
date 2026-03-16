"""FastAPI REST API server for Argus OSINT platform."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from argus.config.settings import ArgusConfig

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Argus OSINT API",
    description="REST API for the Argus OSINT platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

_bearer = HTTPBearer(auto_error=False)
_api_token: str | None = None


def configure_auth(token: str | None) -> None:
    """Set the API bearer token. None disables auth."""
    global _api_token  # noqa: PLW0603
    _api_token = token


async def verify_token(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> None:
    if _api_token is None:
        return  # auth disabled
    if creds is None or creds.credentials != _api_token:
        raise HTTPException(status_code=401, detail="Invalid or missing token")


# ---------------------------------------------------------------------------
# In-memory investigation store (for demo / testing)
# ---------------------------------------------------------------------------

_investigations: dict[str, dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ResolveRequest(BaseModel):
    name: str
    location: str | None = None
    seed_urls: list[str] = Field(default_factory=list)
    email: str | None = None
    username_hint: str | None = None
    phone: str | None = None
    threshold: float | None = None
    platforms: list[str] | None = None


class LinkRequest(BaseModel):
    name: str
    topic: str
    topic_description: str | None = None


class ProfileRequest(BaseModel):
    name: str


class InvestigationResponse(BaseModel):
    investigation_id: str
    status: str


class PlatformInfo(BaseModel):
    name: str
    base_url: str
    rate_limit_per_minute: int
    requires_auth: bool
    requires_playwright: bool
    priority: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post("/investigate", dependencies=[Depends(verify_token)])
async def start_investigation(req: ResolveRequest) -> InvestigationResponse:
    """Start a new investigation (resolve + link + profile) in the background."""
    inv_id = str(uuid.uuid4())[:8]
    _investigations[inv_id] = {
        "id": inv_id,
        "status": "running",
        "target": req.name,
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
        "result": None,
    }
    # Run in background
    asyncio.create_task(_run_investigation(inv_id, req))
    return InvestigationResponse(investigation_id=inv_id, status="running")


@app.get("/investigate/{inv_id}", dependencies=[Depends(verify_token)])
async def get_investigation(inv_id: str) -> dict:
    """Get investigation results."""
    inv = _investigations.get(inv_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return inv


@app.get("/investigate/{inv_id}/report", dependencies=[Depends(verify_token)])
async def get_report(inv_id: str, format: str = "json") -> dict:
    """Get a rendered report for an investigation."""
    inv = _investigations.get(inv_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    if format == "markdown":
        return {"format": "markdown", "content": f"# Report: {inv['target']}\n\nStatus: {inv['status']}"}
    return {"format": "json", "data": inv}


@app.delete("/investigate/{inv_id}", dependencies=[Depends(verify_token)])
async def delete_investigation(inv_id: str) -> dict:
    """Delete an investigation."""
    if inv_id not in _investigations:
        raise HTTPException(status_code=404, detail="Investigation not found")
    del _investigations[inv_id]
    return {"deleted": True}


@app.post("/resolve", dependencies=[Depends(verify_token)])
async def resolve_endpoint(req: ResolveRequest) -> dict:
    """Run resolver only and return results."""
    from argus.agents.resolver import ResolverAgent
    from argus.models.agent import AgentInput
    from argus.models.target import TargetInput

    target = TargetInput(
        name=req.name,
        location=req.location,
        seed_urls=req.seed_urls,
        email=req.email,
        username_hint=req.username_hint,
        phone=req.phone,
    )
    config = ArgusConfig()
    if req.threshold is not None:
        config.verification.minimum_threshold = req.threshold

    agent = ResolverAgent(config=config)
    output = await agent.run(AgentInput(target=target))
    return output.model_dump()


@app.post("/link", dependencies=[Depends(verify_token)])
async def link_endpoint(req: LinkRequest) -> dict:
    """Run linker only and return results."""
    from argus.agents.linker import LinkerAgent, LinkerInput
    from argus.models.target import TargetInput

    agent = LinkerAgent()
    input_data = LinkerInput(
        target=TargetInput(name=req.name),
        topic=req.topic,
        topic_description=req.topic_description,
    )
    output = await agent.run(input_data)
    return output.model_dump()


@app.post("/profile", dependencies=[Depends(verify_token)])
async def profile_endpoint(req: ProfileRequest) -> dict:
    """Run profiler only and return results."""
    from argus.agents.profiler import ProfilerAgent, ProfilerInput
    from argus.models.target import TargetInput

    agent = ProfilerAgent()
    input_data = ProfilerInput(target=TargetInput(name=req.name))
    output = await agent.run(input_data)
    return output.model_dump()


@app.get("/platforms", dependencies=[Depends(verify_token)])
async def list_platforms() -> list[PlatformInfo]:
    """List all registered platforms."""
    from argus.platforms.registry import PlatformRegistry

    registry = PlatformRegistry()
    registry.discover_platforms()
    result = []
    for name in sorted(registry.list_platforms()):
        cls = registry.get_platform(name)
        if cls:
            result.append(
                PlatformInfo(
                    name=cls.name,
                    base_url=cls.base_url,
                    rate_limit_per_minute=cls.rate_limit_per_minute,
                    requires_auth=cls.requires_auth,
                    requires_playwright=cls.requires_playwright,
                    priority=cls.priority,
                )
            )
    return result


@app.get("/investigations", dependencies=[Depends(verify_token)])
async def list_investigations() -> list[dict]:
    """List all stored investigations."""
    return [
        {"id": inv["id"], "target": inv["target"], "status": inv["status"]}
        for inv in _investigations.values()
    ]


# ---------------------------------------------------------------------------
# WebSocket streaming
# ---------------------------------------------------------------------------


@app.websocket("/investigate/{inv_id}/stream")
async def investigation_stream(websocket: WebSocket, inv_id: str) -> None:
    """Stream investigation events via WebSocket."""
    await websocket.accept()
    try:
        # Poll for updates
        prev_status = None
        while True:
            inv = _investigations.get(inv_id)
            if not inv:
                await websocket.send_json(
                    {"event": "error", "data": {"message": "Investigation not found"}}
                )
                break

            if inv["status"] != prev_status:
                prev_status = inv["status"]
                await websocket.send_json({
                    "event": "status_change",
                    "data": {"status": inv["status"]},
                    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                })

            if inv["status"] in ("completed", "failed"):
                await websocket.send_json({
                    "event": "investigation_complete",
                    "data": inv.get("result") or {},
                    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                })
                break

            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass


# ---------------------------------------------------------------------------
# Background investigation runner
# ---------------------------------------------------------------------------


async def _run_investigation(inv_id: str, req: ResolveRequest) -> None:
    """Run full investigation pipeline in background."""
    try:
        from argus.agents.resolver import ResolverAgent
        from argus.models.agent import AgentInput
        from argus.models.target import TargetInput

        target = TargetInput(
            name=req.name,
            location=req.location,
            seed_urls=req.seed_urls,
            email=req.email,
            username_hint=req.username_hint,
            phone=req.phone,
        )
        config = ArgusConfig()
        agent = ResolverAgent(config=config)
        output = await agent.run(AgentInput(target=target))

        _investigations[inv_id]["status"] = "completed"
        _investigations[inv_id]["result"] = output.model_dump()
    except Exception as e:
        _investigations[inv_id]["status"] = "failed"
        _investigations[inv_id]["result"] = {"error": str(e)}
