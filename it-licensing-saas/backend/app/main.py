from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db, get_session
from .routers import vendors, licenses, recommendations, orgs, notifications
import os

app = FastAPI(title="IT Licensing SaaS", version="0.1.0")

# Basic CORS for dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup() -> None:
    init_db()
    if os.getenv("SEED_SAMPLE") == "1":
        from .seeds.seed import seed_sample_vendors
        with get_session() as db:
            seed_sample_vendors(db)

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

app.include_router(orgs.router, prefix="/orgs", tags=["orgs"])
app.include_router(vendors.router, prefix="/vendors", tags=["vendors"])
app.include_router(licenses.router, prefix="/licenses", tags=["licenses"])
app.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
app.include_router(notifications.router, prefix="/notifications", tags=["notifications"])