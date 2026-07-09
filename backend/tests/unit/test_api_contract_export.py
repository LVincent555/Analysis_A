from __future__ import annotations

from fastapi import APIRouter, FastAPI

from scripts.export_api_contract import iter_api_routes


def test_api_contract_export_recurses_nested_included_routers() -> None:
    app = FastAPI()
    parent_router = APIRouter()
    child_router = APIRouter()

    @child_router.post("/api/auth/login")
    async def login() -> dict[str, bool]:
        return {"ok": True}

    parent_router.include_router(child_router)
    app.include_router(parent_router)

    routes = iter_api_routes(app)

    assert [(route.path, route.methods, route.name) for route in routes] == [
        ("/api/auth/login", ["POST"], "login")
    ]
