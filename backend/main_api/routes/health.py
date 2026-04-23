import os

from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
def healthz():
    pexels_key = (os.getenv("PEXELS_API_KEY") or "").strip()
    return {
        "ok": True,
        "capabilities": {
            "pexels": {
                # 仅返回布尔值，不暴露 key 内容
                "configured": bool(pexels_key),
            }
        },
    }
