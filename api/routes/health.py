from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Simple healthcheck endpoint for Render and self-ping keep-awake."""
    return {"status": "ok"}
