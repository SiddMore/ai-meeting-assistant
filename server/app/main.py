from fastapi import FastAPI
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager

from app.api.routes import auth, meetings, transcripts, moms, tasks, webhooks
from app.api.routes.calendar import integrations_router, calendar_router
from app.api.routes import bot_ingest
from app.api.routes import simulate
from app.core.config import settings
from app.db.session import engine
from app.db import base
from app.realtime.socketio_server import sio

# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db.session import init_db
    from app.core.redis import init_redis, close_redis
    try:
        await init_redis()
    except Exception as e:
        import logging
        logging.warning(f"Redis unavailable — token blocklist disabled. ({e})")
    await init_db()
    yield
    try:
        await close_redis()
    except Exception:
        pass
    await engine.dispose()

# ── FastAPI app ───────────────────────────────────────────────────────────────
# ONLY ONE app = FastAPI() call here
app = FastAPI(
    title="AI Meeting Assistant API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json", # This must match what Swagger expects
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True}
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the security scheme for the "Authorize" button
security = HTTPBearer()

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="AI Meeting Assistant",
        version="1.0.0",
        description="Backend API for AI Meeting Assistant",
        routes=app.routes,
    )
    
    # This block specifically adds the "Authorize" lock icon to Swagger
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    openapi_schema["security"] = [{"Bearer": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# ── Routers ───────────────────────────────────────────────────────────────────
API_PREFIX = "/api/v1"
app.include_router(auth.router,            prefix=f"{API_PREFIX}/auth",        tags=["auth"])
app.include_router(meetings.router,        prefix=f"{API_PREFIX}/meetings",    tags=["meetings"])
app.include_router(transcripts.router,     prefix=f"{API_PREFIX}/transcripts", tags=["transcripts"])
app.include_router(moms.router,            prefix=f"{API_PREFIX}/moms",        tags=["moms"])
app.include_router(tasks.router,           prefix=f"{API_PREFIX}/tasks",       tags=["tasks"])
app.include_router(integrations_router,    prefix=API_PREFIX,                  tags=["calendar-integrations"])
app.include_router(calendar_router,        prefix=API_PREFIX,                  tags=["calendar"])
app.include_router(webhooks.router,        prefix=f"{API_PREFIX}/webhooks",    tags=["webhooks"])
app.include_router(bot_ingest.router,      prefix=f"{API_PREFIX}/bot",         tags=["bot-ingest"])
app.include_router(simulate.router,        prefix=f"{API_PREFIX}/simulate",    tags=["simulate (dev)"])

# ── Mount Socket.IO ───────────────────────────────────────────────────────────
import socketio
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)
app.state.sio = sio

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ai-meeting-assistant"}