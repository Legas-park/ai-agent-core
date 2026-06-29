import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from config import settings
from core.plugin_manager import plugin_manager
from core.provider.registry import llm_registry
from core.provider.llm import build_all_providers_from_settings, build_llm_router_from_settings
from core.integrations.registry import integration_registry
from core.integrations.gitlab_client import build_gitlab_client
from core.services.registry import service_registry
from core.services.factory import build_repository_service
from core.setup.repository import assert_repository_startup, check_repository_config
from core.setup.llm import assert_llm_startup, check_llm_config
from routers import webhook

os.makedirs("logs", exist_ok=True)
logger.add("logs/app.log", rotation="00:00", retention="7 days", level="INFO", enqueue=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Agent Core Framework...")

    assert_repository_startup(settings)
    assert_llm_startup(settings)

    all_providers = build_all_providers_from_settings(settings)
    for name, provider in all_providers.items():
        llm_registry.register_provider(name, provider)

    router = build_llm_router_from_settings(settings, all_providers)
    if router is not None:
        llm_registry.register_provider("router", router)
        llm_registry.set_default("router")
    elif all_providers:
        llm_registry.set_default(settings.default_llm_provider)
    else:
        logger.warning(
            "LLM 프로바이더 미구성 — 에이전트 LLM 단계는 드라이런됩니다. "
            "가이드: docs/setup/llm_provider_guide.md"
        )

    repository = build_repository_service(settings)
    service_registry.register("repository", repository)

    if settings.repository_provider == "gitlab":
        integration_registry.register("gitlab", build_gitlab_client(settings))

    plugin_manager.load_plugins()
    logger.info(f"Loaded {len(plugin_manager.plugins)} active plugins.")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Modular AI Agent Core Framework with Pluggable Services",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook.router, prefix="/webhook", tags=["Webhook Gateway"])


@app.get("/health")
async def health_check():
    repository_status = check_repository_config(settings)
    llm_status = check_llm_config(settings)
    return {
        "status": "healthy",
        "version": settings.version,
        "loaded_plugins": [p.name for p in plugin_manager.plugins],
        "startup_mode": repository_status.startup_mode,
        "repository_provider": repository_status.provider,
        "repository_configured": repository_status.configured,
        "repository_missing_fields": repository_status.missing_fields,
        "repository_setup_guide": repository_status.setup_guide,
        "llm_provider": llm_status.provider,
        "llm_model": llm_status.model,
        "llm_configured": llm_status.configured,
        "llm_missing_fields": llm_status.missing_fields,
        "llm_model_doc_url": llm_status.model_doc_url,
        "llm_fallback_chain": llm_status.fallback_chain,
        "llm_setup_guide": llm_status.setup_guide,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_server_host,
        port=settings.api_server_port,
        reload=settings.debug,
    )
