from fastapi import APIRouter, HTTPException, status, Request
from google.cloud import pubsub_v1, tasks_v2
import uuid, os, json, datetime

router = APIRouter()
PUB_TOPIC  = os.getenv("GPU_TOPIC", "gpu-tasks")
TASK_QUEUE = os.getenv("CPU_QUEUE", "cpu-tasks")
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "nca-toolkit-438301")
REGION     = os.getenv("TASKS_REGION", "us-central1") # Updated to us-central1 as per previous steps

publisher = pubsub_v1.PublisherClient()
tasks_cli = tasks_v2.CloudTasksClient()

@router.post("/dispatch", status_code=status.HTTP_202_ACCEPTED)
async def dispatch(req: Request):
    body = await req.json()
    task_type = body.get("task_type")

    # ① 基本バリデーション
    if task_type not in {"gpu","cpu"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="task_type must be 'gpu' or 'cpu'")

    # ② idempotency-key を生成
    idem_key = body.get("idempotency_key") or str(uuid.uuid4())
    body["idempotency_key"] = idem_key

    # ③ GPU 分岐
    if task_type == "gpu":
        # GKEルートが有効かつヘッダーで指定されている場合
        if os.getenv("ENABLE_GKE_ROUTE") == "true" and req.headers.get("X-Destination") == "gke":
            target_topic = "gpu-tasks-gke"
            queued_to = "gke-gpu-topic"
        else:
            target_topic = PUB_TOPIC
            queued_to = "run-gpu-topic"

        file_id = body.get("file_id", "")
        file_type = file_id.split('.')[-1].lower() if '.' in file_id else ''
        
        topic_path = publisher.topic_path(PROJECT_ID, target_topic)
        future = publisher.publish(
            topic_path, 
            json.dumps(body).encode("utf-8"),
            fileType=file_type
        )
        return {"queued_to": queued_to, "id": idem_key, "message_id": future.result()}

    # ④ CPU 分岐
    elif task_type == "cpu":
        parent = tasks_cli.queue_path(PROJECT_ID, REGION, TASK_QUEUE)
        task   = {
            "http_request": {
              "http_method":"POST",
              "url": f"https://no-code-architects-toolkit-340342563048.us-central1.run.app/internal/cpu-task", # Assuming this is the internal endpoint
              "headers":{"Content-Type":"application/json"},
              "body": json.dumps(body).encode()
            }
        }
        created_task = tasks_cli.create_task(parent=parent, task=task)
        return {"queued_to":"cpu-tasks", "id": idem_key, "task_name": created_task.name}
