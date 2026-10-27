from datetime import date

from sqlalchemy import Date, ForeignKey, Index, String, create_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)

from app.config import settings


class Base(DeclarativeBase):
    pass


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    candidate_name: Mapped[str] = mapped_column(String(120))
    candidate_email: Mapped[str] = mapped_column(String(160))
    position: Mapped[str] = mapped_column(String(120))
    interview_date: Mapped[date] = mapped_column(Date)
    # Denormalised mean of question scores so the list view can filter and sort
    # on it without joining and aggregating on every request.
    overall_score: Mapped[int] = mapped_column(index=True)
    # No index: a boolean splits the table roughly in two, so the planner is
    # faster scanning the date index and filtering (0.01ms) than seeking this
    # one and sorting the matches (4.7ms at 100k rows).
    reviewed: Mapped[bool] = mapped_column(default=False)

    questions: Mapped[list["Question"]] = relationship(
        back_populates="interview",
        cascade="all, delete-orphan",
        order_by="Question.position_index",
    )

    # The list endpoint always sorts by (interview_date DESC, id), so each index
    # covers a filter AND that sort. Without the sort columns the planner seeks
    # the filter index and then sorts the matches in a temp B-tree: 3.7ms versus
    # 0.01ms for a position filter at 100k rows.
    # A composite also serves lookups on its leading column, so no separate
    # single-column index on position or interview_date is needed.
    __table_args__ = (
        Index("ix_interviews_date_id", interview_date.desc(), id),
        Index("ix_interviews_position_date", position, interview_date.desc(), id),
    )


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    interview_id: Mapped[str] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE"), index=True
    )
    position_index: Mapped[int]
    prompt: Mapped[str] = mapped_column(String(400))
    response: Mapped[str] = mapped_column(String(2000))
    score: Mapped[int]
    feedback: Mapped[str] = mapped_column(String(600))

    interview: Mapped[Interview] = relationship(back_populates="questions")


_connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)
engine = create_engine(settings.database_url, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session():
    """FastAPI dependency yielding a request-scoped session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
