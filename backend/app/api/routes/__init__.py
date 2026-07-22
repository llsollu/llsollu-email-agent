from fastapi import APIRouter

from app.api.routes import agents, auth, projects, scheduler, templates, webhooks

api_router = APIRouter()
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(projects.router, prefix="/agents", tags=["project_tracker"])
api_router.include_router(scheduler.router, prefix="/agents", tags=["mail_scheduler"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
