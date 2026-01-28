from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.core.config import Settings
from app.services.llm_client import LLMClient
from app.services.reviewer import Reviewer

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()  # type: ignore[call-arg]  # Pydantic Settings loads from .env
    client = LLMClient.from_settings(settings)
    app.state.settings = settings
    app.state.llm_client = client
    app.state.reviewer = Reviewer(client)
    try:
        yield
    finally:
        await client.aclose()

def create_app() -> FastAPI:
    application = FastAPI(title="Code Review Assistant", version="0.1.0", lifespan=lifespan)
    application.include_router(api_router)
    
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        application.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    @application.get("/")
    async def index():
        return FileResponse(str(static_dir / "index.html"))
    
    return application

app = create_app()
