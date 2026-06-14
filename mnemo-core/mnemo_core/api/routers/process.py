from fastapi import APIRouter, Depends, HTTPException

from ...models import DocumentInput, ProcessedDocument
from ...pipeline import PipelineError
from ...pipeline.runner import PipelineRunner
from ..deps import get_runner

router = APIRouter()


@router.post("/api/process", response_model=ProcessedDocument)
async def process(
    req: DocumentInput,
    runner: PipelineRunner = Depends(get_runner),
) -> ProcessedDocument:
    """Classify, augment, and format a document. Returns the structured result without committing."""
    try:
        return await runner.process(req)
    except PipelineError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
