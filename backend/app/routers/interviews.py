from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.db import Interview, get_session
from app.models import (
    ErrorResponse,
    InterviewDetail,
    InterviewPage,
    InterviewSummary,
    ReviewUpdate,
)
from app.queries import (
    ImpossibleFilters,
    InterviewFilters,
    find_interviews,
    get_interview,
)
from app.seed import POSITIONS

# Resolve a caller's casing to the canonical spelling once, so the query can do
# an indexed exact match instead of scanning with lower().
_POSITIONS_BY_LOWER = {p.lower(): p for p in POSITIONS}

router = APIRouter(prefix="/interviews", tags=["interviews"])

NOT_FOUND = {status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}}


def _get_or_404(session: Session, interview_id: str) -> Interview:
    interview = get_interview(session, interview_id)
    if interview is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No interview with id {interview_id!r}.",
        )
    return interview


@router.get(
    "",
    response_model=InterviewPage,
    summary="List candidate interviews",
    description=(
        "Returns a paginated list of interviews with their overall AI score. "
        "All filters are optional and combine with AND."
    ),
)
def list_interviews(
    session: Annotated[Session, Depends(get_session)],
    page: Annotated[int, Query(ge=1, description="1-indexed page number.")] = 1,
    per_page: Annotated[
        int, Query(ge=1, le=100, description="Results per page, capped at 100.")
    ] = 20,
    position: Annotated[
        str | None, Query(description="Exact position match, case-insensitive.")
    ] = None,
    min_score: Annotated[
        int | None, Query(ge=0, le=100, description="Inclusive lower bound on the overall score.")
    ] = None,
    date_from: Annotated[
        date | None, Query(description="Inclusive earliest interview date.")
    ] = None,
    date_to: Annotated[
        date | None, Query(description="Inclusive latest interview date.")
    ] = None,
    q: Annotated[
        str | None, Query(description="Case-insensitive search over candidate name and position.")
    ] = None,
    reviewed: Annotated[
        bool | None, Query(description="Filter by review status.")
    ] = None,
) -> InterviewPage:
    try:
        result = find_interviews(
            session,
            InterviewFilters(
                # An unknown position stays as-is and simply matches nothing.
                position=_POSITIONS_BY_LOWER.get(position.lower(), position)
                if position
                else None,
                min_score=min_score,
                date_from=date_from,
                date_to=date_to,
                q=q,
                reviewed=reviewed,
            ),
            page=page,
            per_page=per_page,
        )
    except ImpossibleFilters as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return InterviewPage(
        items=[InterviewSummary.model_validate(row) for row in result.items],
        page=page,
        per_page=per_page,
        total=result.total,
        total_pages=result.total_pages,
    )


@router.get(
    "/positions",
    response_model=list[str],
    summary="List known positions",
    description="Drives the position filter dropdown so the UI does not hard-code the list.",
)
def list_positions() -> list[str]:
    return sorted(POSITIONS)


@router.get(
    "/{interview_id}",
    response_model=InterviewDetail,
    responses=NOT_FOUND,
    summary="Get one interview in full",
    description=(
        "Returns candidate details plus every question, response, "
        "per-question score and AI feedback."
    ),
)
def read_interview(
    session: Annotated[Session, Depends(get_session)],
    interview_id: Annotated[str, Path(description="Interview UUID.")],
) -> Interview:
    return _get_or_404(session, interview_id)


@router.patch(
    "/{interview_id}",
    response_model=InterviewDetail,
    responses=NOT_FOUND,
    summary="Mark an interview reviewed or unreviewed",
    description="Persists the review status server-side.",
)
def set_reviewed(
    session: Annotated[Session, Depends(get_session)],
    interview_id: Annotated[str, Path(description="Interview UUID.")],
    payload: ReviewUpdate,
) -> Interview:
    interview = _get_or_404(session, interview_id)
    interview.reviewed = payload.reviewed
    session.commit()
    session.refresh(interview)
    return interview
