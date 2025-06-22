from fastapi import FastAPI

# 既存ルーター
from router.ffmpeg import router as ffmpeg_router
from router.cpu_internal import router as cpu_internal_router

# 新ルーター（ハブ機能）
from router.dispatch import router as dispatch_router

app = FastAPI()

# 既存ルートを先にマウント
app.include_router(ffmpeg_router, prefix="/v1")
app.include_router(cpu_internal_router)

# 最後にハブをマウント
app.include_router(dispatch_router)

@app.get("/")
def read_root():
    return {"message": "NCA Toolkit CPU Hub is running."}
