from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .. import __version__
from ..config import Settings, configure_settings, get_settings
from ..jobs import JobManager, JobStore
from ..mcp.server import create_mcp_asgi
from ..observability.logging import setup_logging
from ..observability.telemetry import setup_telemetry
from ..pipeline.runner import PipelineRunner
from .audit import AuditMiddleware
from .auth import require_admin, require_api_token
from .deps import build_runner
from .limits import IntakeLimitsMiddleware
from .routers import health
from .v1 import audit, index, ingest, jobs, process, publish, sources, webhooks


def create_app(cfg: Settings | None = None) -> FastAPI:
    if cfg is not None:
        configure_settings(cfg)

    app = FastAPI(
        title="mnemo-core",
        version=__version__,
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
    v1 = "/api/v1"
    protected = [Depends(require_api_token)]
    app.include_router(ingest.router, prefix=v1, dependencies=protected)
    app.include_router(process.router, prefix=v1, dependencies=protected)
    app.include_router(publish.router, prefix=v1, dependencies=protected)
    app.include_router(jobs.router, prefix=v1, dependencies=protected)
    app.include_router(sources.router, prefix=v1, dependencies=protected)
    app.include_router(index.router, prefix=v1, dependencies=protected)
    app.include_router(
        audit.router,
        prefix=v1,
        dependencies=[Depends(require_api_token), Depends(require_admin)],
    )
    app.include_router(webhooks.router, prefix=v1)

    def runner_factory() -> PipelineRunner:
        return build_runner(get_settings())

    app.mount("/mcp", create_mcp_asgi(runner_factory=runner_factory))

    setup_telemetry(app)

    return app


app = create_app()
