"""Interview queries.

Filtering and paging live here rather than in the route handler so a second
consumer (an export endpoint, a report) reuses the rules instead of copying
them. The handler keeps the HTTP concerns.
"""

import math
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db import Interview

# LIKE treats these as wildcards, so a user searching for a literal one must
# have it escaped or the pattern matches far more than they asked for.
_LIKE_ESCAPE = "\\"


def _escape_like(text: str) -> str:
    for char in (_LIKE_ESCAPE, "%", "_"):
        text = text.replace(char, _LIKE_ESCAPE + char)
    return text


class ImpossibleFilters(ValueError):
    """Filters that cannot match anything, e.g. a date range that runs backwards."""


@dataclass(frozen=True)
class InterviewFilters:
    """Every way the list can be narrowed. All optional, combined with AND."""

    position: str | None = None
    min_score: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    q: str | None = None
    reviewed: bool | None = None

    def validate(self) -> None:
        """Reject filter combinations that can never match.

        An empty result would be technically correct but reads as "no such
        candidates" when the real problem is the dates are the wrong way round.
        """
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ImpossibleFilters(
                "From date must be on or before To date."
            )

    def as_conditions(self) -> list:
        conditions = []
        if self.position:
            # Exact match, not lower(position): wrapping the column makes the
            # index unusable and turns a 0.3ms seek into a 6.9ms scan at 100k
            # rows. The router resolves the caller's casing before we get here.
            conditions.append(Interview.position == self.position)
        if self.min_score is not None:
            conditions.append(Interview.overall_score >= self.min_score)
        if self.date_from:
            conditions.append(Interview.interview_date >= self.date_from)
        if self.date_to:
            conditions.append(Interview.interview_date <= self.date_to)
        if self.reviewed is not None:
            conditions.append(Interview.reviewed.is_(self.reviewed))
        if self.q and self.q.strip():
            term = f"%{_escape_like(self.q.strip().lower())}%"
            conditions.append(
                or_(
                    func.lower(Interview.candidate_name).like(term, escape=_LIKE_ESCAPE),
                    func.lower(Interview.position).like(term, escape=_LIKE_ESCAPE),
                )
            )
        return conditions


@dataclass(frozen=True)
class Page:
    items: list[Interview]
    total: int
    total_pages: int


def find_interviews(
    session: Session, filters: InterviewFilters, page: int, per_page: int
) -> Page:
    """Return one page of matching interviews plus the full match count."""
    filters.validate()
    conditions = filters.as_conditions()

    total = session.scalar(
        select(func.count()).select_from(Interview).where(*conditions)
    ) or 0

    rows = session.scalars(
        select(Interview)
        .where(*conditions)
        # Newest first, then by id so paging is stable when dates tie. This
        # exact order is what the composite indexes in db.py cover; changing it
        # without changing them reintroduces a sort of every matching row.
        .order_by(Interview.interview_date.desc(), Interview.id)
        # shortcut: OFFSET still walks skipped rows, but the covering index makes
        # that ~1ms at 100k. Switch to keyset only if deep paging gets much
        # heavier, and note it breaks "jump to page N".
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()

    return Page(
        items=list(rows),
        total=total,
        total_pages=math.ceil(total / per_page) if total else 0,
    )


def get_interview(session: Session, interview_id: str) -> Interview | None:
    return session.scalar(
        select(Interview)
        .options(selectinload(Interview.questions))
        .where(Interview.id == interview_id)
    )
