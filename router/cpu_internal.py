from fastapi import APIRouter, status

router = APIRouter()

@router.post("/internal/cpu-task", status_code=status.HTTP_200_OK)
async def internal_cpu_task():
    return {"status": "ok"}
