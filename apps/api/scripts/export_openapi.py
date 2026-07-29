"""Dump the FastAPI app's OpenAPI schema to stdout as JSON.

Used to generate frontend TypeScript types (apps/web/src/types/api.generated.ts)
and by CI to detect contract drift between the backend's actual response
models and whatever the frontend last had generated — see
.github/workflows/ci.yml's "Check frontend API types are up to date" step.

Building the app object and calling .openapi() never touches the database or
Redis, so this only needs Settings() to construct without a validation error
— safe placeholder values are fine here, this never runs against real
infrastructure.
"""

import json
import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/db")
os.environ.setdefault("JWT_SECRET", "openapi_export_placeholder_32_chars")
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)
os.environ.setdefault("ANTHROPIC_API_KEY", "placeholder")

from cios.main import app  # noqa: E402

json.dump(app.openapi(), sys.stdout, indent=2)
