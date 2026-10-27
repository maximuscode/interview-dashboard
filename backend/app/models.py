"""Pydantic schemas for the HTTP layer.

Kept separate from the ORM models in `db.py` so the wire format and the storage
schema can move independently.
"""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.ai import band


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    prompt: str
    response: str
    score: int = Field(ge=0, le=100, description="AI-generated score for this answer.")
    feedback: str = Field(description="AI-generated feedback, 1-2 sentences.")

    @computed_field
    @property
    def band(self) -> str:
        """strong, adequate or weak. Sent so the UI need not duplicate the cutoffs."""
        return band(self.score)


class InterviewSummary(BaseModel):
    """List-view shape: no questions, to keep the payload small."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    candidate_name: str
    candidate_email: str
    position: str
    interview_date: date
    overall_score: int = Field(ge=0, le=100)
    reviewed: bool

    @computed_field
    @property
    def band(self) -> str:
        """strong, adequate or weak. Sent so the UI need not duplicate the cutoffs."""
        return band(self.overall_score)


class InterviewDetail(InterviewSummary):
    """Detail-view shape: the summary plus every question."""

    questions: list[QuestionOut]


class InterviewPage(BaseModel):
    """A page of results.

    `total` and `total_pages` are returned so the UI can render real pagination
    instead of inferring whether a next page exists.
    """

    items: list[InterviewSummary]
    page: int
    per_page: int
    total: int
    total_pages: int


class ReviewUpdate(BaseModel):
    reviewed: bool


class ErrorResponse(BaseModel):
    detail: str
