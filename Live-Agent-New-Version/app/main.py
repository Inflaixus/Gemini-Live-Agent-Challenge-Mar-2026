"""FastAPI entrypoint — no business logic here.

Start with:  uvicorn app.main:app --host 0.0.0.0 --port 8080
"""

from app.lifecycle import startup

# Lifecycle must run before FastAPI is constructed so that
# dotenv, logging, config, and the agent are all ready.
startup()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from fastapi.middleware.cors import CORSMiddleware

from app.api.websocket_gateway import router as ws_router
from app.api.health import router as health_router
from app.api.scenarios import router as scenarios_router

app = FastAPI(title="Bilingual Live Audio Agent")

# CORS middleware for UI access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(ws_router)
app.include_router(health_router)
app.include_router(scenarios_router)

# Static files (current test UI — will be removed when UI moves to its own repo)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/index.html")
