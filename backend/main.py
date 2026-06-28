from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
from routers import auth, chat, config_router, plan, user

app = FastAPI(
    title="TripManner API",
    description="AI-powered travel route planning backend",
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth.router, prefix="/api")
app.include_router(user.router, prefix="/api")
app.include_router(plan.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(config_router.router, prefix="/api")


# ---------------------------------------------------------------------------
# Startup: create database tables
# ---------------------------------------------------------------------------
@app.on_event("startup")
def on_startup():
    # Import all models so Base.metadata knows about them
    import models.dialog  # noqa: F401
    import models.mock_route  # noqa: F401
    import models.poi  # noqa: F401
    import models.route  # noqa: F401
    import models.user  # noqa: F401
    import models.user_checkin  # noqa: F401

    Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/api/health", tags=["health"])
async def health_check():
    return {"status": "ok", "service": "TripManner API"}
