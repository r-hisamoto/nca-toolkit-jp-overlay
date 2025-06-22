from fastapi import APIRouter, status

router = APIRouter()

@router.post("/ffmpeg/compose", status_code=status.HTTP_202_ACCEPTED)
async def ffmpeg_compose():
    return {"message": "Request accepted"}
