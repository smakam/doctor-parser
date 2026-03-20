from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.routers import nameboard

settings = get_settings()

app = FastAPI(
    title="Doctor Nameboard Extractor",
    version="1.0.0",
    description="Extract structured doctor profile data from nameboard photos using AI.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(nameboard.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
