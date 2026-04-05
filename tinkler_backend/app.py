from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tinkler_backend.endpoints import register_endpoints


def create_app() -> FastAPI:
    app = FastAPI(
        title="Tinkler Backend",
        version="0.1.0",
        description="HTTP backend for running the Tinkler repo agent.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_endpoints(app)
    return app


app = create_app()

