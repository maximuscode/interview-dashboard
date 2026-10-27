from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect

from app.config import settings
from app.db import engine
from app.routers import interviews


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Seeding runs as its own step so it cannot race across workers; fail
    # loudly here rather than letting every request 500 on a missing table.
    if not inspect(engine).has_table("interviews"):
        raise RuntimeError(
            "Database is not seeded. Run `python -m app.seed` before starting the server."
        )
    yield

app = FastAPI(
    lifespan=lifespan,
    title="Interview Dashboard API",
    version="0.1.0",
    description=(
        "Candidate interview data with mocked AI scoring and feedback.\n\n"
        "Scores are generated once when the database is seeded, so the list and "
        "detail views always agree."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# FastAPI's default 422 body is a list of machine-readable objects. Collapse it
# to the same {"detail": "<sentence>"} shape every other error uses, so the UI
# has one shape to handle and something it can show a person.
_FIELD_LABELS = {
    "min_score": "Minimum score",
    "per_page": "Results per page",
    "date_from": "From date",
    "date_to": "To date",
    "page": "Page",
    "position": "Position",
    "q": "Search",
    "reviewed": "Reviewed",
}


def _readable(error: dict) -> str:
    field = str(error["loc"][-1])
    label = _FIELD_LABELS.get(field, field)
    kind, ctx = error.get("type", ""), error.get("ctx") or {}

    if kind == "greater_than_equal":
        return f"{label} must be {ctx.get('ge')} or more."
    if kind == "less_than_equal":
        return f"{label} must be {ctx.get('le')} or less."
    if kind.startswith("date"):
        return f"{label} must be a valid date."
    if kind in {"int_parsing", "float_parsing"}:
        return f"{label} must be a number."
    if kind == "bool_parsing":
        return f"{label} must be true or false."
    return f"{label}: {error.get('msg', 'is not valid')}"


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        # 422; the named constant was renamed across Starlette versions.
        status_code=422,
        content={"detail": " ".join(_readable(e) for e in exc.errors())},
    )


app.include_router(interviews.router)


@app.get("/health", tags=["meta"], summary="Liveness check")
def health() -> dict[str, str]:
    return {"status": "ok"}
