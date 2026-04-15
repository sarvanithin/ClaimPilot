from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api import routes
from backend.api.v2_routes import v2_router
from backend.fhir.mock_server import fhir_router

app = FastAPI(
    title="ClaimPilot API",
    description="AI Revenue Cycle Management Agent — Prior Auth, Charge Capture, Claim Scrubbing & Appeals",
    version="2.0.0",
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev only. In prod, specify the exact domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# V1 routes (existing — untouched)
app.include_router(routes.router, prefix="/api")

# V2 routes (new RCM pipeline)
app.include_router(v2_router)

# Mock FHIR R4 server
app.include_router(fhir_router)

# Serve frontend static files (production)
_static_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _static_dir.exists():
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    @app.get("/")
    def serve_root():
        return FileResponse(str(_static_dir / "index.html"))

    app.mount("/assets", StaticFiles(directory=str(_static_dir / "assets")), name="static")

    @app.get("/{path:path}")
    def serve_spa(path: str):
        file_path = _static_dir / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_static_dir / "index.html"))
else:
    @app.get("/")
    def root():
        return {
            "message": "Welcome to ClaimPilot API",
            "version": "2.0.0",
            "v1_docs": "/api — Prior Auth Appeal Agent",
            "v2_docs": "/api/v2 — Full RCM Pipeline",
            "fhir_docs": "/fhir — Mock FHIR R4 Server",
        }
