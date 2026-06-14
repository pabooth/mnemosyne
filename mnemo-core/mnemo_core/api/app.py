from collections.abc import Callable

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import Settings, configure_settings, get_settings
from ..mcp.server import create_mcp_asgi
from ..observability.telemetry import setup_telemetry
from .auth import require_api_token
from .deps import build_runner
from .routers import health, ingest, process


def create_app(cfg: Settings | None = None) -> FastAPI:
    if cfg is not None:
        configure_settings(cfg)

    app = FastAPI(
        title="mnemo-core",
        version="0.1.0",
        description="Mnemosyne ingestion engine — REST API and MCP server",
    )
    app.state.settings = get_settings()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[get_settings().frontend_origin, "http://localhost:7000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    protected = [Depends(require_api_token)]
    app.include_router(ingest.router, dependencies=protected)
    app.include_router(process.router, dependencies=protected)

    runner_factory: Callable[[], PipelineRunner] = lambda: build_runner(get_settings())
    app.mount("/mcp", create_mcp_asgi(runner_factory=runner_factory))

    setup_telemetry(app)

    return app


app = create_app()
