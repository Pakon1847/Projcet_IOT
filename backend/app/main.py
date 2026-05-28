import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db, get_influx_client, close_influx
from app.routers import auth, sensor, fan, alert, ai, outdoor, schedule
from app.mqtt_subscriber import mqtt_subscriber, set_event_loop
from app.services.scheduler_service import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────
    init_db()
    get_influx_client()                    # warm up InfluxDB
    set_event_loop(asyncio.get_event_loop())
    mqtt_subscriber.start()
    start_scheduler()                      # Fan schedule checker (every 1 min)
    yield
    # ── Shutdown ─────────────────────────────────────────
    stop_scheduler()
    mqtt_subscriber.stop()
    close_influx()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS — อนุญาต React frontend + PWA
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router,     prefix="/api/auth",     tags=["Auth"])
app.include_router(sensor.router,   prefix="/api/sensor",   tags=["Sensor"])
app.include_router(fan.router,      prefix="/api/fan",      tags=["Fan Control"])
app.include_router(alert.router,    prefix="/api/alert",    tags=["Alert"])
app.include_router(ai.router,       prefix="/api/ai",       tags=["AI"])
app.include_router(outdoor.router,  prefix="/api/outdoor",  tags=["Outdoor Air"])
app.include_router(schedule.router, prefix="/api/schedule", tags=["Fan Schedule"])


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "standard": "กรมควบคุมมลพิษ พ.ศ. 2566",
        "pm25_threshold_24h": f"{settings.PM25_STANDARD_24H} µg/m³",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
