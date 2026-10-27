"""Deterministic fake dataset.

Seeded from `settings.seed`, so the same interviews, scores and feedback come
back on every run. A per-request random score would make the list and detail
views disagree, which reads as a bug.
"""

import random
import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import generate_feedback, overall_score, score_response
from app.config import settings
from app.db import Base, Interview, Question, engine

FIRST_NAMES = [
    "Amara", "Luca", "Priya", "Mateo", "Ingrid", "Omar", "Noor", "Tomas",
    "Sofia", "Kenji", "Elena", "Rhys", "Zara", "Felix", "Nadia", "Idris",
    "Hana", "Pablo", "Yara", "Soren", "Mira", "Dmitri", "Aisha", "Callum",
]

LAST_NAMES = [
    "Okafor", "Bianchi", "Raman", "Alvarez", "Lindqvist", "Haddad", "Chen",
    "Novak", "Moreau", "Tanaka", "Petrova", "Davies", "Khan", "Werner",
    "Osei", "Nakamura", "Silva", "Kowalski", "Bauer", "Fontaine",
]

POSITIONS = [
    "Backend Engineer",
    "Frontend Engineer",
    "Data Scientist",
    "Product Manager",
    "DevOps Engineer",
    "Engineering Manager",
]

# Four shared behavioural questions plus role-specific ones, so a position
# filter surfaces visibly different interviews.
COMMON_QUESTIONS = [
    "Walk me through a project you are proud of and your specific contribution to it.",
    "Describe a time you disagreed with a teammate on a technical decision. How did it resolve?",
    "How do you prioritise when everything on your plate is marked urgent?",
    "Tell me about something you shipped that did not work out. What did you change afterwards?",
]

ROLE_QUESTIONS = {
    "Backend Engineer": [
        "How would you design an API that needs to stay responsive under a 10x traffic spike?",
        "Explain how you would debug a service whose p99 latency tripled overnight.",
        "When would you denormalise a database schema, and what does it cost you?",
    ],
    "Frontend Engineer": [
        "How do you approach making a data-heavy table both fast and accessible?",
        "Describe your strategy for managing server state in a React application.",
        "What does a good loading and error experience look like to you?",
    ],
    "Data Scientist": [
        "How do you tell whether a model improvement is real or an artefact of your split?",
        "Walk me through how you would investigate a sudden drop in a key metric.",
        "How do you communicate model uncertainty to a non-technical stakeholder?",
    ],
    "Product Manager": [
        "How do you decide what not to build in a quarter?",
        "Describe how you would validate a feature idea before committing engineering time.",
        "How do you handle a stakeholder who wants a date before the scope is settled?",
    ],
    "DevOps Engineer": [
        "How would you design a deployment pipeline that makes rollbacks boring?",
        "What belongs in an on-call runbook, and what does not?",
        "How do you decide what to alert on versus what to merely log?",
    ],
    "Engineering Manager": [
        "How do you handle a strong engineer whose work is slipping?",
        "What does your first 90 days with a new team look like?",
        "How do you balance delivery pressure against paying down technical debt?",
    ],
}

RESPONSE_OPENERS = [
    "In my last role I owned this end to end, so",
    "The way I approached it was to start from the constraints, because",
    "I have run into exactly this before, and what worked was",
    "My instinct is to measure first rather than guess, so",
    "I would break it into two parts. First the immediate fix, then",
    "The honest answer is it depends on the team's context, but generally",
]

RESPONSE_BODIES = [
    "I mapped the dependencies before touching anything, which made the risky parts obvious early.",
    "we agreed a narrow definition of done up front and held to it even when scope crept.",
    "I set up a feedback loop that went red on the actual problem before attempting a fix.",
    "the fastest path was to ship a small version, watch how it behaved, then widen it.",
    "I spent time with the people closest to the problem, not just the spec.",
    "we cut the rollout into stages so a mistake could only ever affect a slice of traffic.",
    "I documented the trade-off we accepted so the next person would not relitigate it.",
]


def _candidate_name(rng: random.Random) -> str:
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"


def _email(name: str, index: int) -> str:
    slug = name.lower().replace(" ", ".")
    return f"{slug}{index}@example.com"


def _build_interview(rng: random.Random, index: int, today: date) -> Interview:
    name = _candidate_name(rng)
    position = rng.choice(POSITIONS)

    # Each candidate gets a calibre that shifts all their answers together.
    # Without it, averaging 4-6 independent draws collapses every overall score
    # toward the mean and `min_score` stops discriminating between candidates.
    calibre = rng.triangular(-22, 22, 0)

    prompts = rng.sample(COMMON_QUESTIONS, k=rng.randint(2, 3))
    prompts += rng.sample(ROLE_QUESTIONS[position], k=rng.randint(2, 3))
    rng.shuffle(prompts)

    questions: list[Question] = []
    for order, prompt in enumerate(prompts):
        score = max(0, min(100, round(score_response(rng) + calibre)))
        questions.append(
            Question(
                id=str(uuid.uuid4()),
                position_index=order,
                prompt=prompt,
                response=f"{rng.choice(RESPONSE_OPENERS)} {rng.choice(RESPONSE_BODIES)}",
                score=score,
                feedback=generate_feedback(score, position, rng),
            )
        )

    return Interview(
        id=str(uuid.uuid4()),
        candidate_name=name,
        candidate_email=_email(name, index),
        position=position,
        # Spread across roughly the last six months so date filters have range.
        interview_date=today - timedelta(days=rng.randint(0, 180)),
        overall_score=overall_score([q.score for q in questions]),
        # A minority pre-marked so the reviewed filter is not empty on first load.
        reviewed=rng.random() < 0.25,
        questions=questions,
    )


def build_dataset(seed: int, count: int, today: date | None = None) -> list[Interview]:
    """Generate `count` interviews deterministically from `seed`."""
    rng = random.Random(seed)
    uuid_rng = random.Random(seed + 1)
    # uuid4 reads os.urandom, which the seed cannot reach; patch it so ids are
    # stable too and a reseed does not invalidate bookmarked detail URLs.
    original_uuid4 = uuid.uuid4
    uuid.uuid4 = lambda: uuid.UUID(int=uuid_rng.getrandbits(128), version=4)
    try:
        today = today or date.today()
        return [_build_interview(rng, i, today) for i in range(count)]
    finally:
        uuid.uuid4 = original_uuid4


def init_db() -> None:
    """Create tables and seed them if empty.

    Check-then-insert is only safe because one process runs this. Under
    `uvicorn --workers N` every worker would see an empty table at the same
    time and insert its own copy of the dataset, so the server never calls
    this — `python -m app.seed` does, once, before the server starts.
    """
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        if session.scalar(select(Interview).limit(1)) is not None:
            print(f"Database already seeded at {settings.database_url}")
            return
        session.add_all(build_dataset(settings.seed, settings.interview_count))
        session.commit()
        print(f"Seeded {settings.interview_count} interviews at {settings.database_url}")


if __name__ == "__main__":
    init_db()
