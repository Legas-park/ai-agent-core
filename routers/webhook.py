import json
import hashlib
import hmac
import uuid
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from loguru import logger

from config import settings
from core.plugin_manager import plugin_manager
from core.agent.context import AgentContext
from core.services.payload_normalizer import normalize_pull_request_event

router = APIRouter()


def _verify_signature(request: Request, body: bytes):
    """
    WEBHOOK_SECRET이 설정된 경우 웹훅 요청을 검증합니다.
    - X-Webhook-Secret / X-Gitlab-Token (공통·GitLab)
    - X-Hub-Signature-256 (GitHub HMAC SHA256)
    시크릿이 비어 있으면 검증을 생략합니다.
    """
    secret = settings.webhook_secret
    if not secret:
        return

    header_candidates = (
        request.headers.get("X-Webhook-Secret", ""),
        request.headers.get("X-Gitlab-Token", ""),
    )
    if any(hmac.compare_digest(candidate, secret) for candidate in header_candidates if candidate):
        return

    github_sig = request.headers.get("X-Hub-Signature-256", "")
    if github_sig.startswith("sha256="):
        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        if hmac.compare_digest(github_sig[7:], expected):
            return

    logger.warning("웹훅 서명 검증 실패")
    raise HTTPException(status_code=401, detail="Invalid webhook signature")


@router.post("/gateway")
async def unified_webhook_gateway(request: Request, background_tasks: BackgroundTasks):
    """
    Unified Webhook Gateway
    Analyzes the incoming payload and routes it to the appropriate Service Plugin.
    """
    body = await request.body()
    _verify_signature(request, body)

    try:
        payload = json.loads(body)
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    plugin = plugin_manager.get_handler_for_payload(payload)

    if not plugin:
        logger.info("No suitable plugin found to handle the webhook payload.")
        return {"status": "ignored", "message": "No plugin matched the payload."}

    task_id = str(uuid.uuid4())[:8]
    logger.info(f"[{task_id}] Webhook routed to plugin: {plugin.name}")

    pr_event = normalize_pull_request_event(payload)
    metadata: Dict[str, Any] = {"payload": payload}
    if pr_event is not None:
        metadata["pr_event"] = {
            "provider": pr_event.provider,
            "project_ref": pr_event.ref.project_ref,
            "number": pr_event.ref.number,
            "title": pr_event.ref.title,
            "source_branch": pr_event.ref.source_branch,
        }

    context = AgentContext(task_id=task_id, metadata=metadata)

    orchestrator = plugin.build_orchestrator(payload)
    background_tasks.add_task(orchestrator.run, context)

    return {
        "status": "accepted",
        "message": f"Task delegated to {plugin.name}",
        "task_id": task_id,
    }
