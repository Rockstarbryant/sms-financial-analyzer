"""FastAPI application entrypoint.

Run locally with:
    uvicorn app.main:app --host 127.0.0.1 --port 8000
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analytics, auth, cloud_sync, demo, health, statements, sync, transactions
from app.config import settings
from app.database import init_db


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    init_db()
    yield


app = FastAPI(
    title="SMS Financial Analyzer",
    description=(
        "Personal finance analyzer for M-Pesa and Airtel Money SMS. "
        "Supports local-first (Termux) and cloud multi-user modes."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

# Local origins always allowed; extra origins come from SMS_ANALYZER_CORS_ORIGINS
# for cloud deployments.
_default_origins = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins + settings.extra_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(demo.router)
app.include_router(statements.router)
app.include_router(sync.router)          # local Termux sync (no auth)
app.include_router(cloud_sync.router)    # cloud companion-app sync (JWT required)
app.include_router(transactions.router)
app.include_router(analytics.router)
