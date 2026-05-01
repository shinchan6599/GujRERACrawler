from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.client import GujReraClient
from app.config import get_settings
from app.db.store import LocalStore
from app.logging import configure_logging
from app.routers.listing import router as listing_router
from app.routers.pages import router as pages_router
from app.routers.project import router as project_router
from app.routers.rag import router as rag_router
from app.routers.storage import router as storage_router

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.gujrera_client = GujReraClient(settings)
    app.state.local_store = LocalStore(settings.local_db_path)
    await app.state.local_store.init()
    app.state.sync_tasks = {}
    try:
        yield
    finally:
        for task in app.state.sync_tasks.values():
            if not task.done():
                task.cancel()
        app.state.local_store.close()
        await app.state.gujrera_client.close()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(pages_router)
app.include_router(listing_router)
app.include_router(project_router)
app.include_router(storage_router)
app.include_router(rag_router)
