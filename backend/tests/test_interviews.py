"""Endpoint tests.

Written against the HTTP surface — the public seam — so they survive a
refactor of the storage layer.
"""

from sqlalchemy import text


def ids(payload) -> list[str]:
    return [item["id"] for item in payload["items"]]


class TestPagination:
    def test_returns_all_rows_on_one_page(self, client):
        body = client.get("/interviews").json()
        assert body["total"] == 5
        assert body["total_pages"] == 1
        assert len(body["items"]) == 5

    def test_splits_across_pages_without_overlap(self, client):
        first = client.get("/interviews", params={"per_page": 2, "page": 1}).json()
        second = client.get("/interviews", params={"per_page": 2, "page": 2}).json()

        assert first["total_pages"] == 3  # 5 rows at 2 per page
        assert len(first["items"]) == 2
        assert set(ids(first)).isdisjoint(ids(second))

    def test_last_page_is_partial(self, client):
        body = client.get("/interviews", params={"per_page": 2, "page": 3}).json()
        assert len(body["items"]) == 1
        assert body["total"] == 5

    def test_page_beyond_the_end_is_empty_not_an_error(self, client):
        body = client.get("/interviews", params={"per_page": 2, "page": 99}).json()
        assert body["items"] == []
        assert body["total"] == 5

    def test_orders_newest_first(self, client):
        body = client.get("/interviews").json()
        assert ids(body) == ["i5", "i4", "i3", "i2", "i1"]


class TestFilters:
    def test_position_filter_is_case_insensitive(self, client):
        body = client.get("/interviews", params={"position": "backend engineer"}).json()
        assert sorted(ids(body)) == ["i1", "i2"]

    def test_min_score_is_inclusive(self, client):
        body = client.get("/interviews", params={"min_score": 75}).json()
        assert sorted(ids(body)) == ["i1", "i2", "i5"]

    def test_date_range_is_inclusive_at_both_ends(self, client):
        body = client.get(
            "/interviews",
            params={"date_from": "2026-02-20", "date_to": "2026-04-10"},
        ).json()
        assert sorted(ids(body)) == ["i2", "i3", "i4"]

    def test_reviewed_filter(self, client):
        body = client.get("/interviews", params={"reviewed": "true"}).json()
        assert sorted(ids(body)) == ["i2", "i5"]

    def test_search_matches_name_or_position(self, client):
        by_name = client.get("/interviews", params={"q": "grace"}).json()
        assert ids(by_name) == ["i2"]

        by_position = client.get("/interviews", params={"q": "data sci"}).json()
        assert sorted(ids(by_position)) == ["i3", "i4"]

    def test_search_treats_like_wildcards_as_literal_text(self, client):
        # Unescaped, "%" and "_" are LIKE wildcards and match every row.
        for wildcard in ("%", "_", "%%"):
            body = client.get("/interviews", params={"q": wildcard}).json()
            assert body["total"] == 0, f"{wildcard!r} matched {body['total']} rows"

    def test_search_finds_a_literal_underscore(self, client):
        body = client.get("/interviews", params={"q": "o_o"}).json()
        assert body["total"] == 0

    def test_filters_combine_with_and(self, client):
        body = client.get(
            "/interviews", params={"position": "Backend Engineer", "min_score": 80}
        ).json()
        assert ids(body) == ["i1"]

    def test_no_matches_returns_an_empty_page_not_a_404(self, client):
        body = client.get("/interviews", params={"min_score": 99}).json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["total_pages"] == 0


class TestEdgeCases:
    """Inputs a user actually produces: stale links, backwards ranges, odd text."""

    def test_backwards_date_range_explains_itself(self, client):
        response = client.get(
            "/interviews", params={"date_from": "2026-06-01", "date_to": "2026-01-01"}
        )
        assert response.status_code == 422
        assert response.json()["detail"] == "From date must be on or before To date."

    def test_same_day_range_is_allowed(self, client):
        body = client.get(
            "/interviews", params={"date_from": "2026-01-10", "date_to": "2026-01-10"}
        ).json()
        assert ids(body) == ["i1"]

    def test_unknown_position_is_an_empty_page_not_an_error(self, client):
        body = client.get("/interviews", params={"position": "Astronaut"}).json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_blank_search_is_ignored_rather_than_matching_nothing(self, client):
        body = client.get("/interviews", params={"q": "   "}).json()
        assert body["total"] == 5

    def test_very_long_search_does_not_error(self, client):
        body = client.get("/interviews", params={"q": "a" * 5000}).json()
        assert body["total"] == 0

    def test_per_page_larger_than_the_dataset(self, client):
        body = client.get("/interviews", params={"per_page": 100}).json()
        assert len(body["items"]) == 5
        assert body["total_pages"] == 1

    def test_min_score_zero_keeps_everything(self, client):
        body = client.get("/interviews", params={"min_score": 0}).json()
        assert body["total"] == 5

    def test_min_score_one_hundred_is_allowed(self, client):
        body = client.get("/interviews", params={"min_score": 100}).json()
        assert body["total"] == 0


class TestDetail:
    def test_returns_questions_with_scores_and_feedback(self, client):
        body = client.get("/interviews/i1").json()
        assert body["candidate_name"] == "Ada Lovelace"
        assert [q["score"] for q in body["questions"]] == [90, 90]
        assert all(q["feedback"] for q in body["questions"])

    def test_detail_score_agrees_with_the_list(self, client):
        listed = next(
            item for item in client.get("/interviews").json()["items"] if item["id"] == "i3"
        )
        detail = client.get("/interviews/i3").json()
        assert detail["overall_score"] == listed["overall_score"] == 55

    def test_unknown_id_returns_404(self, client):
        response = client.get("/interviews/does-not-exist")
        assert response.status_code == 404
        assert "detail" in response.json()


class TestValidation:
    def test_rejects_per_page_below_one(self, client):
        assert client.get("/interviews", params={"per_page": 0}).status_code == 422

    def test_rejects_per_page_above_the_cap(self, client):
        assert client.get("/interviews", params={"per_page": 500}).status_code == 422

    def test_rejects_out_of_range_min_score(self, client):
        assert client.get("/interviews", params={"min_score": 150}).status_code == 422

    def test_rejects_malformed_date(self, client):
        assert client.get("/interviews", params={"date_from": "nonsense"}).status_code == 422

    def test_validation_errors_are_a_readable_sentence(self, client):
        # FastAPI's default 422 body is a list of objects. The UI shows `detail`
        # to a person, so it must be a string they can act on.
        body = client.get("/interviews", params={"min_score": 101}).json()
        assert body["detail"] == "Minimum score must be 100 or less."

    def test_every_rejected_param_names_itself(self, client):
        cases = {
            "page": ({"page": 0}, "Page must be 1 or more."),
            "per_page": ({"per_page": 500}, "Results per page must be 100 or less."),
            "min_score": ({"min_score": -1}, "Minimum score must be 0 or more."),
            "date_from": ({"date_from": "nope"}, "From date must be a valid date."),
            "reviewed": ({"reviewed": "maybe"}, "Reviewed must be true or false."),
        }
        for name, (params, expected) in cases.items():
            body = client.get("/interviews", params=params).json()
            assert body["detail"] == expected, f"{name}: got {body['detail']!r}"


class TestReviewToggle:
    def test_flag_persists_to_a_later_read(self, client):
        assert client.patch("/interviews/i1", json={"reviewed": True}).status_code == 200
        assert client.get("/interviews/i1").json()["reviewed"] is True

        listed = next(
            item for item in client.get("/interviews").json()["items"] if item["id"] == "i1"
        )
        assert listed["reviewed"] is True

    def test_can_be_unset(self, client):
        client.patch("/interviews/i2", json={"reviewed": False})
        assert client.get("/interviews/i2").json()["reviewed"] is False

    def test_patch_unknown_id_returns_404(self, client):
        assert client.patch("/interviews/nope", json={"reviewed": True}).status_code == 404

    def test_patch_without_a_body_is_rejected_readably(self, client):
        response = client.patch("/interviews/i1", json={})
        assert response.status_code == 422
        assert response.json()["detail"] == "Reviewed: Field required"

    def test_patch_is_idempotent(self, client):
        for _ in range(2):
            client.patch("/interviews/i1", json={"reviewed": True})
        assert client.get("/interviews/i1").json()["reviewed"] is True


class TestMeta:
    def test_positions_endpoint_feeds_the_filter_dropdown(self, client):
        positions = client.get("/interviews/positions").json()
        assert "Backend Engineer" in positions
        assert positions == sorted(positions)

    def test_openapi_schema_is_served(self, client):
        schema = client.get("/openapi.json").json()
        assert "/interviews" in schema["paths"]
        assert "/interviews/{interview_id}" in schema["paths"]


class TestFeedbackQuality:
    """The brief asks for scoring 'based on specific job requirements', so
    feedback must reference the role and never contradict its own score."""

    def test_feedback_names_the_role_requirement(self):
        import random

        from app.ai import REQUIREMENTS, generate_feedback

        feedback = generate_feedback(90, "Backend Engineer", random.Random(0))
        assert REQUIREMENTS["Backend Engineer"] in feedback

    def test_unknown_position_falls_back_rather_than_raising(self):
        import random

        from app.ai import DEFAULT_REQUIREMENT, generate_feedback

        feedback = generate_feedback(50, "Astronaut", random.Random(0))
        assert DEFAULT_REQUIREMENT in feedback

    def test_api_sends_the_band_so_the_ui_need_not_duplicate_cutoffs(self, client):
        listed = {i["id"]: i for i in client.get("/interviews").json()["items"]}
        assert listed["i1"]["band"] == "strong"      # 90
        assert listed["i2"]["band"] == "adequate"    # 75
        assert listed["i4"]["band"] == "weak"        # 40

    def test_band_boundaries_are_inclusive(self):
        from app.ai import band

        assert band(80) == "strong"
        assert band(79) == "adequate"
        assert band(60) == "adequate"
        assert band(59) == "weak"

    def test_verdict_matches_the_score_band(self):
        import random

        from app.ai import generate_feedback

        assert "Strong evidence" in generate_feedback(95, "Data Scientist", random.Random(0))
        assert "Partial evidence" in generate_feedback(70, "Data Scientist", random.Random(0))
        assert "Little evidence" in generate_feedback(30, "Data Scientist", random.Random(0))


class TestIndexes:
    """The list endpoint always sorts by (interview_date DESC, id). An index that
    covers only the filter makes the planner sort matches in a temp B-tree, which
    cost 3.7ms versus 0.01ms for a position filter at 100k rows."""

    def _plan(self, sql, params=None):
        from app.db import get_session
        from app.main import app

        session = next(app.dependency_overrides[get_session]())
        try:
            rows = session.execute(text("EXPLAIN QUERY PLAN " + sql), params or {})
            return " | ".join(row[-1] for row in rows)
        finally:
            session.close()

    def test_default_list_sorts_straight_off_an_index(self, client):
        plan = self._plan(
            "SELECT * FROM interviews ORDER BY interview_date DESC, id LIMIT 10"
        )
        assert "ix_interviews_date_id" in plan
        assert "TEMP B-TREE" not in plan

    def test_position_filter_uses_the_composite_index(self, client):
        plan = self._plan(
            "SELECT * FROM interviews WHERE position = :p "
            "ORDER BY interview_date DESC, id LIMIT 10",
            {"p": "Backend Engineer"},
        )
        assert "ix_interviews_position_date" in plan
        assert "TEMP B-TREE" not in plan

    def test_position_filter_is_not_wrapped_in_lower(self):
        # lower(position) makes the index unusable; the router normalises casing
        # instead so the query can compare the column directly.
        from app.queries import InterviewFilters

        sql = str(InterviewFilters(position="Backend Engineer").as_conditions()[0])
        assert "lower" not in sql.lower()
