"""Mocked AI evaluation.

This is the single seam where a real model call would go. Everything else in
the app treats scoring as a black box that turns a question and a response into
a number plus a sentence or two of feedback.

Feedback is written against the job requirement the question probes, because the
brief scores responses "based on specific job requirements" — generic praise
tells a recruiter nothing about fit for the role.
"""

import random

# Score bands drive which feedback pool is used, so the wording and the number
# can never contradict each other. The API returns the band name with every
# score so the UI colours badges from this definition instead of its own copy.
STRONG = 80
ADEQUATE = 60


def band(score: int) -> str:
    """Return the band name for a score: strong, adequate or weak."""
    if score >= STRONG:
        return "strong"
    if score >= ADEQUATE:
        return "adequate"
    return "weak"


_STRONG_FEEDBACK = [
    "Clear, well-structured answer with concrete examples that directly address the question.",
    "Demonstrates strong command of the topic and backs claims with specifics from past work.",
    "Thorough response that covers trade-offs as well as the chosen approach.",
    "Confident and precise, with good awareness of how the decision affected the wider system.",
]

_ADEQUATE_FEEDBACK = [
    "Reasonable answer, though it stays general where a concrete example would be stronger.",
    "Covers the main idea but leaves the trade-offs and failure cases unexplored.",
    "Solid grasp of the fundamentals; the reasoning would benefit from more depth.",
    "Addresses the question adequately but does not go beyond the obvious approach.",
]

_WEAK_FEEDBACK = [
    "Response is vague and does not engage with the specifics of the question.",
    "Misses key aspects of the problem and offers little supporting reasoning.",
    "Limited depth; the answer restates the question rather than answering it.",
    "Struggles to articulate a clear approach, with several points left unsupported.",
]


def score_response(rng: random.Random) -> int:
    """Return a plausible 0-100 score.

    Uses a triangular distribution peaking at 76 so results look like a real
    candidate pool — mostly competent, with a thin tail at either end — rather
    than uniform noise.
    """
    return round(rng.triangular(25, 99, 76))


# The competency each role is actually being assessed on. A real model call
# would take these from the job description rather than a lookup table.
REQUIREMENTS = {
    "Backend Engineer": "designing systems that hold up under load",
    "Frontend Engineer": "building interfaces that stay fast and accessible",
    "Data Scientist": "drawing defensible conclusions from messy data",
    "Product Manager": "prioritising ruthlessly and justifying the cut",
    "DevOps Engineer": "making deploys and recovery routine",
    "Engineering Manager": "growing a team while still shipping",
}

DEFAULT_REQUIREMENT = "the core demands of this role"

# One band drives both the wording pool and the verdict, so they cannot drift.
_BY_BAND = {
    "strong": (_STRONG_FEEDBACK, "Strong evidence of"),
    "adequate": (_ADEQUATE_FEEDBACK, "Partial evidence of"),
    "weak": (_WEAK_FEEDBACK, "Little evidence of"),
}


def generate_feedback(score: int, position: str, rng: random.Random) -> str:
    """Return 1-2 sentences of feedback consistent with `score` and the role.

    The second sentence names the requirement being assessed, so a recruiter
    reads the score as evidence of fit rather than as an isolated number.
    """
    pool, verdict = _BY_BAND[band(score)]
    requirement = REQUIREMENTS.get(position, DEFAULT_REQUIREMENT)
    return f"{rng.choice(pool)} {verdict} {requirement}."


def overall_score(question_scores: list[int]) -> int:
    """Interview-level score: the rounded mean of its per-question scores.

    Derived rather than drawn independently so the list and detail views always
    agree with each other.
    """
    # No caller can pass an empty list today, but a silently-zero interview is
    # a worse failure than this branch, so the guard stays.
    if not question_scores:
        return 0
    return round(sum(question_scores) / len(question_scores))
