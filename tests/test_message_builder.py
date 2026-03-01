# pyright: reportPrivateUsage=false
from datetime import UTC, datetime

from telegram_notifier.message_builder import (
    _format_duration,
    _format_job_line,
    _job_icon,
    build_legacy_message,
    build_pipeline_message,
    determine_overall_status,
)
from telegram_notifier.models import JobInfo, WorkflowContext


def _make_job(
    name: str = "Test",
    status: str = "completed",
    conclusion: str | None = "success",
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> JobInfo:
    return JobInfo(
        name=name,
        status=status,
        conclusion=conclusion,
        started_at=started_at,
        completed_at=completed_at,
    )


def _make_ctx() -> WorkflowContext:
    return WorkflowContext(
        server_url="https://github.com",
        repository="org/repo",
        workflow_name="CI",
        ref="main",
        sha="abc1234567890",
        run_id="42",
    )


# --- build_legacy_message ---


def test_legacy_message_contains_all_fields() -> None:
    message = build_legacy_message(
        github_url="https://github.com",
        repo_name="kruchenburger/telegram-notifier",
        workflow_name="CI",
        ref="main",
        commit="abc1234567890",
        run_id="12345",
        status="success",
    )
    assert "kruchenburger/telegram-notifier" in message
    assert "CI" in message
    assert "main" in message
    assert "abc1234" in message
    assert "success" in message
    assert "\U0001f7e2" in message


def test_legacy_message_failure() -> None:
    message = build_legacy_message(
        github_url="https://github.com",
        repo_name="org/repo",
        workflow_name="Test",
        ref="dev",
        commit="deadbeef1234567",
        run_id="99",
        status="failure",
    )
    assert "\U0001f534" in message


def test_legacy_message_cancelled() -> None:
    message = build_legacy_message(
        github_url="https://github.com",
        repo_name="org/repo",
        workflow_name="Test",
        ref="dev",
        commit="deadbeef1234567",
        run_id="99",
        status="cancelled",
    )
    assert "\u26aa\ufe0f" in message


def test_legacy_message_unknown_status() -> None:
    message = build_legacy_message(
        github_url="https://github.com",
        repo_name="org/repo",
        workflow_name="Test",
        ref="dev",
        commit="deadbeef1234567",
        run_id="99",
        status="skipped",
    )
    assert "\u2753" in message


def test_legacy_message_html_links() -> None:
    message = build_legacy_message(
        github_url="https://github.com",
        repo_name="org/repo",
        workflow_name="CI",
        ref="main",
        commit="abc1234567890",
        run_id="42",
        status="success",
    )
    assert '<a href="https://github.com/org/repo">' in message
    assert '<a href="https://github.com/org/repo/actions/runs/42">' in message
    assert '<a href="https://github.com/org/repo/tree/main">' in message
    assert '<a href="https://github.com/org/repo/commit/abc1234567890">' in message


# --- _format_duration ---


def test_format_duration_minutes_and_seconds() -> None:
    started = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    completed = datetime(2026, 1, 1, 12, 2, 15, tzinfo=UTC)
    assert _format_duration(started, completed) == "2m 15s"


def test_format_duration_seconds_only() -> None:
    started = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    completed = datetime(2026, 1, 1, 12, 0, 45, tzinfo=UTC)
    assert _format_duration(started, completed) == "45s"


def test_format_duration_not_started() -> None:
    assert _format_duration(None, None) == ""


def test_format_duration_no_completed() -> None:
    started = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    assert _format_duration(started, None) == ""


# --- _job_icon ---


def test_job_icon_success() -> None:
    assert _job_icon(_make_job(conclusion="success")) == "\u2705"


def test_job_icon_failure() -> None:
    assert _job_icon(_make_job(conclusion="failure")) == "\u274c"


def test_job_icon_skipped() -> None:
    assert _job_icon(_make_job(conclusion="skipped")) == "\u23ed\ufe0f"


def test_job_icon_in_progress() -> None:
    assert _job_icon(_make_job(status="in_progress", conclusion=None)) == "\U0001f504"


def test_job_icon_queued() -> None:
    assert _job_icon(_make_job(status="queued", conclusion=None)) == "\u23f3"


# --- _format_job_line ---


def test_format_job_line_with_duration() -> None:
    job = _make_job(
        name="Build",
        started_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
        completed_at=datetime(2026, 1, 1, 12, 1, 30, tzinfo=UTC),
    )
    line = _format_job_line(job)
    assert "\u2705" in line
    assert "Build" in line
    assert "1m 30s" in line


def test_format_job_line_without_duration() -> None:
    job = _make_job(name="Deploy", status="queued", conclusion=None)
    line = _format_job_line(job)
    assert "\u23f3" in line
    assert "Deploy" in line
    assert "<i>" not in line


# --- determine_overall_status ---


def test_overall_status_all_success() -> None:
    jobs = [_make_job(conclusion="success"), _make_job(conclusion="success")]
    assert determine_overall_status(jobs) == "success"


def test_overall_status_success_with_skipped() -> None:
    jobs = [_make_job(conclusion="success"), _make_job(conclusion="skipped")]
    assert determine_overall_status(jobs) == "success"


def test_overall_status_any_failure() -> None:
    jobs = [_make_job(conclusion="success"), _make_job(conclusion="failure")]
    assert determine_overall_status(jobs) == "failure"


def test_overall_status_in_progress() -> None:
    jobs = [
        _make_job(conclusion="success"),
        _make_job(status="in_progress", conclusion=None),
    ]
    assert determine_overall_status(jobs) == "in_progress"


def test_overall_status_queued() -> None:
    jobs = [
        _make_job(conclusion="success"),
        _make_job(status="queued", conclusion=None),
    ]
    assert determine_overall_status(jobs) == "in_progress"


def test_overall_status_cancelled() -> None:
    jobs = [_make_job(conclusion="success"), _make_job(conclusion="cancelled")]
    assert determine_overall_status(jobs) == "cancelled"


def test_overall_status_failure_takes_precedence() -> None:
    jobs = [
        _make_job(conclusion="failure"),
        _make_job(status="queued", conclusion=None),
    ]
    assert determine_overall_status(jobs) == "failure"


# --- build_pipeline_message ---


def test_pipeline_message_all_success() -> None:
    ctx = _make_ctx()
    jobs = [
        _make_job(
            name="Lint",
            started_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
            completed_at=datetime(2026, 1, 1, 12, 0, 23, tzinfo=UTC),
        ),
        _make_job(
            name="Test",
            started_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
            completed_at=datetime(2026, 1, 1, 12, 1, 42, tzinfo=UTC),
        ),
    ]
    message = build_pipeline_message(ctx, jobs)
    assert "\U0001f7e2" in message  # green circle
    assert "CI" in message
    assert "org/repo" in message
    assert "\u2705 Lint" in message
    assert "\u2705 Test" in message
    assert "23s" in message
    assert "1m 42s" in message


def test_pipeline_message_with_pending() -> None:
    ctx = _make_ctx()
    jobs = [
        _make_job(name="Lint"),
        _make_job(name="Build", status="queued", conclusion=None),
    ]
    message = build_pipeline_message(ctx, jobs)
    assert "\U0001f7e1" in message  # yellow circle
    assert "\u23f3 Build" in message


def test_pipeline_message_with_failure() -> None:
    ctx = _make_ctx()
    jobs = [
        _make_job(name="Lint"),
        _make_job(name="Test", conclusion="failure"),
    ]
    message = build_pipeline_message(ctx, jobs)
    assert "\U0001f534" in message  # red circle
    assert "\u274c Test" in message
