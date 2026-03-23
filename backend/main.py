"""FastAPI application."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .middleware import SiteGateMiddleware
from .routers import admin, auth, leaderboard, predictions, tournaments, users

app = FastAPI(
    title="Quiniela API",
    description="Chess tournament prediction system",
)

# Site gate first, CORS outermost so preflight (OPTIONS) succeeds before gate check
app.add_middleware(SiteGateMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tournaments.router)
app.include_router(leaderboard.router)
app.include_router(predictions.router)
app.include_router(admin.router)
app.include_router(users.router)


@app.on_event("startup")
def startup():
    init_db()
