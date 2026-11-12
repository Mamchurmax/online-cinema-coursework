"""Aggregates all v1 routers."""

from fastapi import APIRouter

from app.api.v1 import admin, auth, billing, catalog, health, me, playback, recommendations

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(catalog.router)
api_router.include_router(playback.router)
api_router.include_router(billing.router)
api_router.include_router(recommendations.router)
api_router.include_router(admin.router)
