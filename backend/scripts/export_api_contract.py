"""Export the current FastAPI route contract.

Run with analysis dependencies because legacy aggregate routers import the
analysis stack:

    uv run --extra analysis python scripts/export_api_contract.py
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

from fastapi.routing import APIRoute

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")
os.environ.setdefault("ALLOW_INSECURE_DEV_KEYS", "true")


@dataclass(frozen=True, slots=True)
class RouteContract:
    path: str
    methods: list[str]
    name: str
    endpoint: str


def _iter_api_route_objects(route_items: Iterable[Any]) -> Iterator[APIRoute]:
    for item in route_items:
        if isinstance(item, APIRoute):
            yield item
            continue

        router = getattr(item, "original_router", None)
        nested_routes = getattr(router, "routes", None)
        if nested_routes:
            yield from _iter_api_route_objects(nested_routes)


def iter_api_routes(fastapi_app: Any | None = None) -> list[RouteContract]:
    if fastapi_app is None:
        from app.main import app as fastapi_app

    routes: list[RouteContract] = []

    for route in _iter_api_route_objects(fastapi_app.routes):
        methods = sorted((route.methods or set()) - {"HEAD", "OPTIONS"})
        endpoint = route.endpoint
        routes.append(
            RouteContract(
                path=route.path,
                methods=methods,
                name=route.name,
                endpoint=f"{endpoint.__module__}.{endpoint.__name__}",
            )
        )

    return sorted(routes, key=lambda item: (item.path, item.methods, item.name))


def main() -> None:
    print(json.dumps([asdict(route) for route in iter_api_routes()], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
