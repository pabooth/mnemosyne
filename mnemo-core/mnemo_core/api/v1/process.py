import logging

from fastapi import APIRouter, Depends, HTTPException

from ...models import DocumentInput, ProcessedDocument
from ...pipeline import PipelineError
from ...pipeline.runner import PipelineRunner
from ..deps import get_runner

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/process", response_model=ProcessedDocument)
async def process(
    req: DocumentInput,
    runner: PipelineRunner = Depends(get_runner),
) -> ProcessedDocument:
    """Classify, augment, and format a document. Returns the structured result without committing."""
    try:
        return await runner.process(req)
    except PipelineError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception:
        logger.exception("Unexpected error during process")
        raise HTTPException(status_code=500, detail="Internal server error") from None
