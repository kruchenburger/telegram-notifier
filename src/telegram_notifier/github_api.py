from __future__ import annotations

import logging
from datetime import datetime

import httpx

from telegram_notifier.models import JobInfo

logger = logging.getLogger(__name__)

_GITHUB_API_BASE = "https://api.github.com"


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse ISO-8601 datetime string from GitHub API."""
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _get_next_url(link_header: str | None) -> str | None:
    """Extract the 'next' URL from a GitHub Link header."""
    if link_header is None:
        return None
    for part in link_header.split(","):
        if 'rel="next"' in part:
            return part.split(";")[0].strip().strip("<>")
    return None


async def fetch_workflow_jobs(
    github_token: str,
    repository: str,
    run_id: str,
) -> list[JobInfo]:
    """Fetch all jobs for a workflow run from the GitHub REST API.

    Handles pagination via Link headers.
    """
    url: str | None = (
        f"{_GITHUB_API_BASE}/repos/{repository}/actions/runs/{run_id}/jobs"
    )
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    params: dict[str, str | int] | None = {
        "filter": "latest",
        "per_page": 100,
    }

    jobs: list[JobInfo] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        while url is not None:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            for job in data["jobs"]:
                jobs.append(
                    JobInfo(
                        name=job["name"],
                        status=job["status"],
                        conclusion=job.get("conclusion"),
                        started_at=_parse_datetime(job.get("started_at")),
                        completed_at=_parse_datetime(job.get("completed_at")),
                    )
                )

            url = _get_next_url(response.headers.get("link"))
            params = None  # Params are embedded in the next URL

    return jobs


async def fetch_pr_title(
    github_token: str,
    repository: str,
    pr_number: str,
) -> str | None:
    """Fetch PR title from the GitHub REST API."""
    url = f"{_GITHUB_API_BASE}/repos/{repository}/pulls/{pr_number}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers=headers)
        if response.status_code != 200:
            logger.warning(
                "Failed to fetch PR #%s: %s", pr_number, response.status_code
            )
            return None
        data = response.json()
        title: str = data["title"]
        return title


def filter_jobs(
    jobs: list[JobInfo],
    exclude_patterns: list[str],
) -> list[JobInfo]:
    """Filter out jobs matching any exclude pattern (case-insensitive substring)."""
    if not exclude_patterns:
        return jobs
    normalized = [p.strip().lower() for p in exclude_patterns if p.strip()]
    if not normalized:
        return jobs
    return [
        job
        for job in jobs
        if not any(pattern in job.name.lower() for pattern in normalized)
    ]
