from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.v2_routes import v2_router
from backend.fhir.mock_server import fhir_router

# V1 routes require langchain (heavy deps) — optional for deployment
try:
    from backend.api import routes as v1_routes
    _v1_available = True
except ImportError:
    _v1_available = False

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

# V1 routes (existing — requires langchain)
if _v1_available:
    app.include_router(v1_routes.router, prefix="/api")
else:
    # Lightweight fallback so the Appeal Agent tab works without langchain
    from backend.api.v1_fallback import v1_fallback_router
    app.include_router(v1_fallback_router, prefix="/api")

# V2 routes (new RCM pipeline)
app.include_router(v2_router)

# Mock FHIR R4 server
app.include_router(fhir_router)


# Seed demo data on startup
@app.on_event("startup")
async def _seed_demo_data():
    from backend.seed_demo import seed_pipeline
    count = await seed_pipeline()
    if count:
        print(f"[ClaimPilot] Seeded {count} demo claims into pipeline")

# Serve frontend static files (production)
_static_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _static_dir.exists():
    from starlette.responses import FileResponse
    from starlette.staticfiles import StaticFiles

    class SPAStaticFiles(StaticFiles):
        """Serve index.html for any path not found (SPA routing)."""
        async def get_response(self, path, scope):
            try:
                return await super().get_response(path, scope)
            except Exception:
                return await super().get_response("index.html", scope)

    app.mount("/", SPAStaticFiles(directory=str(_static_dir), html=True), name="spa")
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
