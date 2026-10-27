"""Test fixtures.

Each test runs against its own in-memory SQLite database populated with a small
hand-written dataset, not the generated seed. Expected values in the tests are
therefore literals derived from that fixture rather than recomputed with the
same logic the endpoints use.
"""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, Interview, Question, get_session
from app.main import app

# (id, name, position, date, reviewed, [question scores])
FIXTURE_ROWS = [
    ("i1", "Ada Lovelace", "Backend Engineer", date(2026, 1, 10), False, [90, 90]),
    ("i2", "Grace Hopper", "Backend Engineer", date(2026, 2, 20), True, [70, 80]),
    ("i3", "Alan Turing", "Data Scientist", date(2026, 3, 30), False, [50, 60]),
    ("i4", "Katherine Johnson", "Data Scientist", date(2026, 4, 10), False, [40, 40]),
    ("i5", "Linus Torvalds", "Product Manager", date(2026, 5, 15), True, [100, 80]),
]

# Overall score is the mean of the question scores above, written out by hand.
EXPECTED_SCORES = {"i1": 90, "i2": 75, "i3": 55, "i4": 40, "i5": 90}


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with TestingSession() as session:
        for row_id, name, position, when, reviewed, scores in FIXTURE_ROWS:
            session.add(
                Interview(
                    id=row_id,
                    candidate_name=name,
                    candidate_email=f"{row_id}@example.com",
                    position=position,
                    interview_date=when,
                    overall_score=EXPECTED_SCORES[row_id],
                    reviewed=reviewed,
                    questions=[
                        Question(
                            id=f"{row_id}-q{n}",
                            position_index=n,
                            prompt=f"Question {n}?",
                            response="An answer.",
                            score=score,
                            feedback="Some feedback.",
                        )
                        for n, score in enumerate(scores)
                    ],
                )
            )
        session.commit()

    def _override():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    # Bypass the startup seeder: these tests supply their own data.
    app.dependency_overrides[get_session] = _override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
