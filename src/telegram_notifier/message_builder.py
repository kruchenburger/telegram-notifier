from __future__ import annotations

from datetime import datetime

from telegram_notifier.models import JobInfo, WorkflowContext

_JOB_ICONS: dict[str | None, str] = {
    "success": "\u2705",
    "failure": "\u274c",
    "cancelled": "\u26aa\ufe0f",
    "skipped": "\u23ed\ufe0f",
}

_PIPELINE_ICONS: dict[str, str] = {
    "success": "\U0001f7e2",
    "failure": "\U0001f534",
    "cancelled": "\u26aa\ufe0f",
    "in_progress": "\U0001f7e1",
}


def _format_duration(started: datetime | None, completed: datetime | None) -> str:
    """Format job duration as 'Xm Ys' or 'Xs'."""
    if started is None or completed is None:
        return ""
    total_seconds = int((completed - started).total_seconds())
    if total_seconds < 0:
        return ""
    minutes, seconds = divmod(total_seconds, 60)
    if minutes > 0:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def _job_icon(job: JobInfo) -> str:
    """Get the status icon for a job."""
    if job.status == "completed":
        return _JOB_ICONS.get(job.conclusion, "\u2753")
    if job.status == "in_progress":
        return "\U0001f504"
    return "\u23f3"


def _format_job_line(job: JobInfo) -> str:
    """Format a single job as one line of the message."""
    icon = _job_icon(job)
    duration = _format_duration(job.started_at, job.completed_at)
    duration_part = f"  <i>{duration}</i>" if duration else ""
    return f"  {icon} {job.name}{duration_part}"


def determine_overall_status(jobs: list[JobInfo]) -> str:
    """Determine the overall pipeline status from individual job statuses."""
    conclusions = [j.conclusion for j in jobs if j.status == "completed"]

    if any(c == "failure" for c in conclusions):
        return "failure"
    if any(j.status in ("in_progress", "queued") for j in jobs):
        return "in_progress"
    if any(c == "cancelled" for c in conclusions):
        return "cancelled"
    if all(c in ("success", "skipped") for c in conclusions) and conclusions:
        return "success"
    return "in_progress"


def build_pipeline_message(
    ctx: WorkflowContext,
    jobs: list[JobInfo],
) -> str:
    """Build the full pipeline progress HTML message."""
    overall = determine_overall_status(jobs)
    icon = _PIPELINE_ICONS.get(overall, "\u2753")

    header = f'{icon} <b><a href="{ctx.workflow_url}">{ctx.workflow_name}</a></b>\n'
    meta = (
        f'<b>Repo:</b> <a href="{ctx.repo_url}">{ctx.repository}</a>\n'
        f'<b>Branch:</b> <a href="{ctx.ref_url}">{ctx.ref}</a>\n'
        f'<b>Commit:</b> <a href="{ctx.commit_url}">{ctx.sha:.7}</a>\n'
    )
    job_lines = "\n".join(_format_job_line(job) for job in jobs)

    return f"{header}{meta}\n{job_lines}"


def build_legacy_message(
    *,
    github_url: str,
    repo_name: str,
    workflow_name: str,
    ref: str,
    commit: str,
    run_id: str,
    status: str,
) -> str:
    """Build an HTML-formatted notification message (v1 legacy mode)."""
    repo_url = f"{github_url}/{repo_name}"
    ref_url = f"{repo_url}/tree/{ref}"
    commit_url = f"{repo_url}/commit/{commit}"
    workflow_url = f"{repo_url}/actions/runs/{run_id}"

    status_map = {
        "success": "\U0001f7e2",
        "failure": "\U0001f534",
        "cancelled": "\u26aa\ufe0f",
    }
    status_icon = status_map.get(status.lower(), "\u2753")

    return (
        f'<b>Repository:</b> <a href="{repo_url}">{repo_name}</a>\n'
        f'<b>Workflow:</b> <a href="{workflow_url}">{workflow_name}</a>\n'
        f'<b>Branch:</b> <a href="{ref_url}">{ref}</a>\n'
        f'<b>Commit:</b> <a href="{commit_url}">{commit:.7}</a>\n'
        f"<b>Status:</b> {status} {status_icon}"
    )
