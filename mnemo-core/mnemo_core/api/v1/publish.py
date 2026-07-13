import logging

from fastapi import APIRouter, Depends, HTTPException

from ...models import ProcessedDocument, PublishResult
from ...pipeline import PipelineError
from ...pipeline.runner import PipelineRunner
from ..deps import get_runner

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/publish", response_model=PublishResult)
async def publish(
    req: ProcessedDocument,
    runner: PipelineRunner = Depends(get_runner),
) -> PublishResult:
    """Publish an edited preview, then apply the ADR-011 adversarial review gate."""
    try:
        return await runner.publish(req)
    except PipelineError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception:
        logger.exception("Unexpected error during publish")
        raise HTTPException(status_code=500, detail="Internal server error") from None
