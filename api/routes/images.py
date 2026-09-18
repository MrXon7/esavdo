import os
import mimetypes
import tempfile
import httpx
from fastapi import APIRouter, HTTPException, Response
from core.config import settings

router = APIRouter(tags=["Images"])

# Temporary on-disk / memory cache for images
CACHE_DIR = os.path.join(tempfile.gettempdir(), "esavdo_img_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# In-memory LRU-like dictionary cache (capped at 100 items to conserve memory)
MEMORY_CACHE: dict[str, tuple[bytes, str]] = {}
MAX_MEMORY_ITEMS = 100


@router.get("/images/{file_id}")
async def get_image(file_id: str):
    """
    Proxies Telegram files via getFile and caches them locally.
    Never exposes BOT_TOKEN to the frontend.
    """
    # 1. Check in-memory cache
    if file_id in MEMORY_CACHE:
        content, content_type = MEMORY_CACHE[file_id]
        return Response(
            content=content,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=604800, immutable"},
        )

    # 2. Check disk cache
    cache_path = os.path.join(CACHE_DIR, f"{file_id}.cached")
    meta_path = os.path.join(CACHE_DIR, f"{file_id}.meta")

    if os.path.exists(cache_path) and os.path.exists(meta_path):
        try:
            with open(cache_path, "rb") as f:
                content = f.read()
            with open(meta_path, "r", encoding="utf-8") as f:
                content_type = f.read().strip() or "image/jpeg"

            # Store into memory cache
            if len(MEMORY_CACHE) >= MAX_MEMORY_ITEMS:
                MEMORY_CACHE.pop(next(iter(MEMORY_CACHE)))
            MEMORY_CACHE[file_id] = (content, content_type)

            return Response(
                content=content,
                media_type=content_type,
                headers={"Cache-Control": "public, max-age=604800, immutable"},
            )
        except Exception:
            pass

    # 3. Fetch from Telegram API
    get_file_url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/getFile"

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(get_file_url, params={"file_id": file_id})
            data = resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Telegram API ulanishda xatolik: {e}")

        if not data.get("ok"):
            raise HTTPException(status_code=404, detail="Rasm Telegram serverlarida topilmadi")

        file_path = data.get("result", {}).get("file_path")
        if not file_path:
            raise HTTPException(status_code=404, detail="Rasm manzili (file_path) topilmadi")

        download_url = f"https://api.telegram.org/file/bot{settings.BOT_TOKEN}/{file_path}"
        try:
            img_resp = await client.get(download_url)
            img_resp.raise_for_status()
            content = img_resp.content
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Rasmni yuklab olishda xatolik: {e}")

        content_type, _ = mimetypes.guess_type(file_path)
        if not content_type:
            content_type = "image/jpeg"

        # Save to disk cache
        try:
            with open(cache_path, "wb") as f:
                f.write(content)
            with open(meta_path, "w", encoding="utf-8") as f:
                f.write(content_type)
        except Exception:
            pass

        # Save to memory cache
        if len(MEMORY_CACHE) >= MAX_MEMORY_ITEMS:
            MEMORY_CACHE.pop(next(iter(MEMORY_CACHE)))
        MEMORY_CACHE[file_id] = (content, content_type)

        return Response(
            content=content,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=604800, immutable"},
        )
