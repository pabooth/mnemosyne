from fastapi import APIRouter, Depends, HTTPException

from ...models import DocumentInput, IngestResult
from ...pipeline import PipelineError
from ...pipeline.runner import PipelineRunner
from ..deps import get_runner

router = APIRouter()


@router.post("/api/ingest", response_model=IngestResult)
async def ingest(
    req: DocumentInput,
    runner: PipelineRunner = Depends(get_runner),
) -> IngestResult:
    """Full pipeline in one call: classify, augment, format, commit, and raise a PR."""
    try:
        return await runner.run(req)
    except PipelineError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
