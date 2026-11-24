"""hackViz FastAPI application.

Run (from backend/):  uvicorn app.main:app --host 127.0.0.1 --port 8000
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from .config import settings
from .routes import activity, anomalies, employees, export, extension, system
from .seed import seed
from .services.worker import worker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("hackviz")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Initialising PostgreSQL schema and dataset ...")
    result = seed(verbose=False)  # creates tables; imports the fictional dataset only if missing
    log.info("Dataset: %s", result)
    worker.start()
    log.info("Analysis worker started (auto=%s, batch=%s, idle=%ss, model=%s)", settings.auto_analysis,
             settings.batch_size, settings.idle_seconds, settings.ollama_model)
    yield
    worker.stop()


app = FastAPI(title="hackViz API", version="1.0.0", lifespan=lifespan,
              description="AI-assisted insider-risk detection (local PostgreSQL + local Ollama).")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"^chrome-extension://[a-p]{32}$",
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(OperationalError)
async def db_down(_: Request, exc: OperationalError):
    return JSONResponse(status_code=503, content={"detail": "PostgreSQL is unavailable",
                                                  "error": str(exc.orig).splitlines()[0][:200]})


@app.exception_handler(RequestValidationError)
async def bad_request(_: Request, exc: RequestValidationError):
    errs = [{"field": ".".join(str(p) for p in e["loc"][1:]) or "body", "message": e["msg"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": "; ".join(f"{e['field']}: {e['message']}" for e in errs),
                                                  "errors": errs})


for r in (system.router, employees.router, activity.router, anomalies.router, export.router, extension.router):
    app.include_router(r)


@app.get("/")
def root():
    return {"name": "hackViz API", "docs": "/docs", "health": "/api/health"}
