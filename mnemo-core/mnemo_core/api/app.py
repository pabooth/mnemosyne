from collections.abc import Callable

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import Settings, configure_settings, get_settings
from ..mcp.server import create_mcp_asgi
from ..jobs import JobManager, JobStore
from ..observability.logging import setup_logging
from ..observability.telemetry import setup_telemetry
from ..pipeline.runner import PipelineRunner
from .auth import require_api_token
from .auth import require_admin
from .audit import AuditMiddleware
from .deps import build_runner
from .limits import IntakeLimitsMiddleware
from .routers import audit, health, ingest, jobs, process, publish, sources, webhooks


def create_app(cfg: Settings | None = None) -> FastAPI:
    if cfg is not None:
        configure_settings(cfg)

    app = FastAPI(
        title="mnemo-core",
        version="0.1.0",
        description="Mnemosyne ingestion engine — REST API and MCP server",
    )
    app.state.settings = get_settings()
    app.state.job_store = JobStore(app.state.settings.state_db_path)
    app.state.job_manager = JobManager(
        app.state.job_store,
        max_attempts=app.state.settings.job_max_attempts,
        retry_base_seconds=app.state.settings.job_retry_base_seconds,
    )
    setup_logging(app.state.settings.log_level)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[get_settings().frontend_origin, "http://localhost:8888"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(IntakeLimitsMiddleware, cfg=app.state.settings)
    app.add_middleware(AuditMiddleware)

    app.include_router(health.router)
    protected = [Depends(require_api_token)]
    app.include_router(ingest.router, dependencies=protected)
    app.include_router(process.router, dependencies=protected)
    app.include_router(publish.router, dependencies=protected)
    app.include_router(jobs.router, dependencies=protected)
    app.include_router(sources.router, dependencies=protected)
    app.include_router(
        audit.router,
        dependencies=[Depends(require_api_token), Depends(require_admin)],
    )
    app.include_router(webhooks.router)

    runner_factory: Callable[[], PipelineRunner] = lambda: build_runner(get_settings())
    app.mount("/mcp", create_mcp_asgi(runner_factory=runner_factory))

    setup_telemetry(app)

    return app


app = create_app()
