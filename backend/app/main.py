import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from time import perf_counter

from app.auth.routes import router as auth_router
from app.auth.security import hash_password
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.metrics import HTTP_REQUESTS, HTTP_REQUEST_DURATION
from app.core.rate_limit import RateLimitMiddleware
from app.database.base import Base
from app.database.models import Permission, Role, RolePermission, User
from app.database.session import SessionLocal, engine
from app.api import alerts, analytics, fraud, investigations, model_monitoring, system, transactions
from app.streaming.kafka_consumer import consumer_worker
from app.streaming.kafka_producer import publisher

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        role_descriptions = {
            "administrator": "Full platform administration",
            "fraud_analyst": "Review transactions and investigate alerts",
            "investigator": "Manage investigation cases and alert outcomes",
            "ml_engineer": "Manage model artifacts and model promotion workflow",
            "read_only_auditor": "Read-only access for audit and oversight",
        }
        permission_descriptions = {
            "read": "Read dashboards, transactions and alerts",
            "investigate": "Manage alerts and investigation cases",
            "manage_users": "Manage user and access configuration",
            "manage_models": "Manage model registry and promotion decisions",
            "ingest": "Ingest transaction events",
        }
        role_permissions = {
            "administrator": set(permission_descriptions),
            "fraud_analyst": {"read", "investigate", "ingest"},
            "investigator": {"read", "investigate"},
            "ml_engineer": {"read", "manage_models", "ingest"},
            "read_only_auditor": {"read"},
        }
        for name, description in role_descriptions.items():
            if db.get(Role, name) is None:
                db.add(Role(name=name, description=description))
        for name, description in permission_descriptions.items():
            if db.get(Permission, name) is None:
                db.add(Permission(name=name, description=description))
        db.flush()
        for role_name, permissions in role_permissions.items():
            for permission_name in permissions:
                exists = db.get(RolePermission, (role_name, permission_name))
                if exists is None:
                    db.add(RolePermission(role_name=role_name, permission_name=permission_name))
        if not db.query(User).filter(User.email == settings.admin_email).first():
            db.add(User(email=settings.admin_email, hashed_password=hash_password(settings.admin_password),
                        role="administrator", is_active=True))
        db.commit()
        logger.warning("Local bootstrap user configured. Change its password and JWT secret before exposure.")
    finally:
        db.close()
    consumer_worker.start()
    yield
    consumer_worker.stop()
    publisher.close()


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan,
              description="Event-driven fraud detection and risk intelligence demo.")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True,
                   allow_methods=["GET", "POST", "PATCH", "OPTIONS"], allow_headers=["Authorization", "Content-Type"])
app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.rate_limit_per_minute,
                   excluded_paths={"/", "/health", "/api/v1/metrics", "/api/v1/monitoring/metrics"})
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(transactions.router, prefix=settings.api_prefix)
app.include_router(fraud.router, prefix=settings.api_prefix)
app.include_router(alerts.router, prefix=settings.api_prefix)
app.include_router(investigations.router, prefix=settings.api_prefix)
app.include_router(analytics.router, prefix=settings.api_prefix)
app.include_router(model_monitoring.router, prefix=settings.api_prefix)
app.include_router(system.router, prefix=settings.api_prefix)


@app.middleware("http")
async def observe_http_requests(request: Request, call_next):
    started = perf_counter()
    response = await call_next(request)
    route = getattr(request.scope.get("route"), "path", "unmatched")
    HTTP_REQUESTS.labels(request.method, route, str(response.status_code)).inc()
    HTTP_REQUEST_DURATION.labels(request.method, route).observe(perf_counter() - started)
    return response


@app.get("/")
def root():
    return {"name": settings.app_name, "docs": "/docs", "api_prefix": settings.api_prefix}


@app.get("/health")
def root_health():
    return {"status": "ok", "service": "fraud-intelligence-api"}
