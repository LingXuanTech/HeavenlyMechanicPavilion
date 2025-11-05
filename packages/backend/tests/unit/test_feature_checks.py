"""Unit tests for feature completeness checks."""

from __future__ import annotations

import pytest

from app.services import feature_checks as fc


def test_run_feature_checks_collects_results(monkeypatch: pytest.MonkeyPatch) -> None:
    """run_feature_checks should return results for each registered check."""

    def passing_check() -> tuple[bool, str | None]:
        return True, None

    def failing_check() -> tuple[bool, str | None]:
        return False, "failure"

    monkeypatch.setattr(
        fc,
        "FEATURE_CHECKS",
        [
            fc.FeatureCheckDefinition("pass", "passing", passing_check),
            fc.FeatureCheckDefinition("fail", "failing", failing_check),
        ],
        raising=False,
    )

    results = fc.run_feature_checks()
    assert len(results) == 2
    assert results[0].passed is True
    assert results[1].passed is False
    assert results[1].detail == "failure"

    summary = fc.summarize_feature_checks(results)
    assert summary.passed == 1
    assert summary.failed == 1
    assert summary.total == 2
    assert summary.status == "incomplete"


def test_run_feature_checks_handles_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exceptions raised by checks should be captured and surfaced."""

    def raising_check() -> tuple[bool, str | None]:
        raise RuntimeError("boom")

    monkeypatch.setattr(
        fc,
        "FEATURE_CHECKS",
        [fc.FeatureCheckDefinition("explode", "raises", raising_check)],
        raising=False,
    )

    results = fc.run_feature_checks()
    assert len(results) == 1
    assert results[0].passed is False
    assert "RuntimeError" in (results[0].detail or "")


def test_default_feature_checks_all_pass() -> None:
    """The default feature checks should reflect a complete implementation."""

    results = fc.run_feature_checks()
    assert results, "Expected at least one feature check to be registered"
    assert all(result.passed for result in results)

    summary = fc.summarize_feature_checks(results)
    assert summary.status == "complete"
    assert summary.failed == 0
