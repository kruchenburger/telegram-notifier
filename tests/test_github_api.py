# pyright: reportPrivateUsage=false
import httpx
import pytest
import respx

from telegram_notifier.github_api import (
    _get_next_url,
    _parse_datetime,
    fetch_pr_title,
    fetch_workflow_jobs,
    filter_jobs,
)
from telegram_notifier.models import JobInfo

# --- _parse_datetime ---


def test_parse_datetime_iso_format() -> None:
    result = _parse_datetime("2026-01-15T10:30:00Z")
    assert result is not None
    assert result.year == 2026
    assert result.month == 1
    assert result.hour == 10


def test_parse_datetime_none() -> None:
    assert _parse_datetime(None) is None


# --- _get_next_url ---


def test_get_next_url_with_next() -> None:
    base = "https://api.github.com/repos/org/repo/actions/runs/1/jobs"
    header = f'<{base}?page=2>; rel="next", <{base}?page=3>; rel="last"'
    assert _get_next_url(header) == f"{base}?page=2"


def test_get_next_url_without_next() -> None:
    base = "https://api.github.com/repos/org/repo/actions/runs/1/jobs"
    header = f'<{base}?page=1>; rel="last"'
    assert _get_next_url(header) is None


def test_get_next_url_none() -> None:
    assert _get_next_url(None) is None


# --- filter_jobs ---


def _make_job(name: str) -> JobInfo:
    return JobInfo(
        name=name,
        status="completed",
        conclusion="success",
        started_at=None,
        completed_at=None,
    )


def test_filter_jobs_excludes_matching() -> None:
    jobs = [_make_job("Lint"), _make_job("Test"), _make_job("Notify")]
    result = filter_jobs(jobs, ["notify"])
    assert len(result) == 2
    assert all(j.name != "Notify" for j in result)


def test_filter_jobs_case_insensitive() -> None:
    jobs = [_make_job("Lint"), _make_job("TRACKER")]
    result = filter_jobs(jobs, ["tracker"])
    assert len(result) == 1
    assert result[0].name == "Lint"


def test_filter_jobs_empty_patterns() -> None:
    jobs = [_make_job("Lint"), _make_job("Test")]
    result = filter_jobs(jobs, [])
    assert len(result) == 2


def test_filter_jobs_whitespace_patterns() -> None:
    jobs = [_make_job("Lint"), _make_job("Test")]
    result = filter_jobs(jobs, ["  ", ""])
    assert len(result) == 2


def test_filter_jobs_multiple_patterns() -> None:
    jobs = [_make_job("Lint"), _make_job("Notify-1"), _make_job("Notify-2")]
    result = filter_jobs(jobs, ["notify"])
    assert len(result) == 1


# --- fetch_workflow_jobs ---


@respx.mock
@pytest.mark.asyncio
async def test_fetch_workflow_jobs_parses_response() -> None:
    respx.get("https://api.github.com/repos/org/repo/actions/runs/123/jobs").mock(
        return_value=httpx.Response(
            200,
            json={
                "total_count": 2,
                "jobs": [
                    {
                        "name": "Lint",
                        "status": "completed",
                        "conclusion": "success",
                        "started_at": "2026-01-01T12:00:00Z",
                        "completed_at": "2026-01-01T12:00:23Z",
                    },
                    {
                        "name": "Test",
                        "status": "in_progress",
                        "conclusion": None,
                        "started_at": "2026-01-01T12:00:05Z",
                        "completed_at": None,
                    },
                ],
            },
        )
    )

    jobs = await fetch_workflow_jobs("fake-token", "org/repo", "123")

    assert len(jobs) == 2
    assert jobs[0].name == "Lint"
    assert jobs[0].status == "completed"
    assert jobs[0].conclusion == "success"
    assert jobs[0].started_at is not None
    assert jobs[1].name == "Test"
    assert jobs[1].status == "in_progress"
    assert jobs[1].conclusion is None


# --- fetch_pr_title ---


@respx.mock
@pytest.mark.asyncio
async def test_fetch_pr_title_success() -> None:
    respx.get("https://api.github.com/repos/org/repo/pulls/1").mock(
        return_value=httpx.Response(
            200,
            json={"title": "Add pipeline tracking", "number": 1},
        )
    )

    title = await fetch_pr_title("fake-token", "org/repo", "1")
    assert title == "Add pipeline tracking"


@respx.mock
@pytest.mark.asyncio
async def test_fetch_pr_title_not_found() -> None:
    respx.get("https://api.github.com/repos/org/repo/pulls/999").mock(
        return_value=httpx.Response(404)
    )

    title = await fetch_pr_title("fake-token", "org/repo", "999")
    assert title is None
