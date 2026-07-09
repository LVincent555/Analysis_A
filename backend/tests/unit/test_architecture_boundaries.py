from __future__ import annotations

import ast
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
CONTEXTS_ROOT = BACKEND_ROOT / "app" / "contexts"

FORBIDDEN_DOMAIN_IMPORTS = (
    "fastapi",
    "sqlalchemy",
    "jose",
    "jwt",
    "app.auth",
    "app.core.caching",
    "app.database",
    "app.db_models",
    "app.routers",
    "app.services",
)

FORBIDDEN_APPLICATION_IMPORTS = (
    "fastapi",
    "sqlalchemy",
    "jose",
    "jwt",
    "app.auth",
    "app.core",
    "app.database",
    "app.db_models",
    "app.routers",
    "app.services",
)


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.append(node.module)

    return modules


def test_context_domain_layers_do_not_import_framework_or_infrastructure() -> None:
    domain_files = list(CONTEXTS_ROOT.glob("*/domain/**/*.py"))
    assert domain_files, "expected context domain files to exist"

    violations: list[str] = []
    for path in domain_files:
        for module in _imported_modules(path):
            if module.startswith(FORBIDDEN_DOMAIN_IMPORTS):
                violations.append(f"{path.relative_to(BACKEND_ROOT)} imports {module}")

    assert violations == []


def test_context_application_layers_do_not_import_framework_or_legacy_modules() -> None:
    application_files = list(CONTEXTS_ROOT.glob("*/application/**/*.py"))
    assert application_files, "expected context application files to exist"

    violations: list[str] = []
    for path in application_files:
        for module in _imported_modules(path):
            if module.startswith(FORBIDDEN_APPLICATION_IMPORTS):
                violations.append(f"{path.relative_to(BACKEND_ROOT)} imports {module}")

    assert violations == []


def test_contexts_have_hexagonal_layers() -> None:
    expected_layers = {"api", "application", "domain", "infrastructure"}
    context_dirs = [
        path for path in CONTEXTS_ROOT.iterdir()
        if path.is_dir() and not path.name.startswith("_")
    ]

    assert {path.name for path in context_dirs} >= {
        "identity",
        "market_data",
        "analysis",
        "board_heat",
        "operations",
    }

    missing: list[str] = []
    for context_dir in context_dirs:
        for layer in expected_layers:
            if not (context_dir / layer).is_dir():
                missing.append(f"{context_dir.name}/{layer}")

    assert missing == []
