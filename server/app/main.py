from fastapi import FastAPI
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager
import logging
import os
import anyio

# Alembic imports for auto-migration
from alembic.config import Config
from alembic import command

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
    # 1. Enable pgvector extension
    logging.info("Ensuring pgvector extension is enabled...")
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        logging.info("pgvector extension is ready.")
    except Exception as e:
        logging.error(f"Failed to enable pgvector: {e}")

    # 2. Run Database Migrations / Sync
    logging.info("Checking for database migrations...")
    try:
        ini_path = os.path.join(os.getcwd(), "alembic.ini")
        if os.path.exists(ini_path):
            alembic_cfg = Config(ini_path)
            
            try:
                # Try to upgrade normally
                await anyio.to_thread.run_sync(command.upgrade, alembic_cfg, "head")
                logging.info("Database migrations applied successfully.")
            except Exception as migrate_err:
                # If it fails because tables already exist, "Stamp" the head
                if "already exists" in str(migrate_err):
                    logging.info("Tables already exist. Stamping database version...")
                    await anyio.to_thread.run_sync(command.stamp, alembic_cfg, "head")
                    logging.info("Database version synced with Alembic.")
                else:
                    raise migrate_err
        else:
            logging.warning("alembic.ini not found.")
    except Exception as e:
        logging.error(f"Migration/Sync error: {e}")

    # 3. Initialize Redis (REMOVED init_db as Alembic handles this now)
    from app.core.redis import init_redis, close_redis
    try:
        await init_redis()
    except Exception as e:
        logging.warning(f"Redis unavailable — token blocklist disabled. ({e})")
    
    yield
    
    # 4. Cleanup
    try:
        await close_redis()
    except Exception:
        pass
    await engine.dispose()

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Meeting Assistant API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
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
app.include_router(auth.router,             prefix=f"{API_PREFIX}/auth",        tags=["auth"])
app.include_router(meetings.router,         prefix=f"{API_PREFIX}/meetings",    tags=["meetings"])
app.include_router(transcripts.router,      prefix=f"{API_PREFIX}/transcripts", tags=["transcripts"])
app.include_router(moms.router,             prefix=f"{API_PREFIX}/moms",        tags=["moms"])
app.include_router(tasks.router,            prefix=f"{API_PREFIX}/tasks",       tags=["tasks"])
app.include_router(integrations_router,     prefix=API_PREFIX,                  tags=["calendar-integrations"])
app.include_router(calendar_router,         prefix=API_PREFIX,                  tags=["calendar"])
app.include_router(webhooks.router,         prefix=f"{API_PREFIX}/webhooks",    tags=["webhooks"])
app.include_router(bot_ingest.router,       prefix=f"{API_PREFIX}/bot",         tags=["bot-ingest"])
app.include_router(simulate.router,         prefix=f"{API_PREFIX}/simulate",    tags=["simulate (dev)"])

# ── Mount Socket.IO ───────────────────────────────────────────────────────────
import socketio
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)
app.state.sio = sio

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ai-meeting-assistant"}