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
    "in_progress": "\U0001f504",
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
    # Don't show duration for skipped/cancelled jobs — they didn't really run
    if job.conclusion in ("skipped", "cancelled"):
        return f"  {icon} {job.name}"
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


def _total_duration(jobs: list[JobInfo]) -> str:
    """Calculate total pipeline duration from earliest start to latest completion."""
    ran = [j for j in jobs if j.conclusion not in ("skipped", "cancelled")]
    starts = [j.started_at for j in ran if j.started_at is not None]
    ends = [j.completed_at for j in ran if j.completed_at is not None]
    if not starts or not ends:
        return ""
    return _format_duration(min(starts), max(ends))


def build_pipeline_message(
    ctx: WorkflowContext,
    jobs: list[JobInfo],
) -> str:
    """Build the full pipeline progress HTML message."""
    overall = determine_overall_status(jobs)
    icon = _PIPELINE_ICONS.get(overall, "\u2753")

    header = f'{icon} <b><a href="{ctx.workflow_url}">{ctx.workflow_name}</a></b>\n'

    # Show PR title if available, otherwise branch
    if ctx.pr_title is not None and ctx.pr_url is not None:
        ref_line = f'<b>PR:</b> <a href="{ctx.pr_url}">{ctx.pr_title}</a>\n'
    else:
        ref_line = f'<b>Branch:</b> <a href="{ctx.ref_url}">{ctx.ref}</a>\n'

    meta = (
        f'<b>Repo:</b> <a href="{ctx.repo_url}">{ctx.repository}</a>\n'
        f"{ref_line}"
        f'<b>Commit:</b> <a href="{ctx.commit_url}">{ctx.sha:.7}</a>\n'
        f'<b>Author:</b> <a href="{ctx.server_url}/{ctx.actor}">{ctx.actor}</a>\n'
    )
    job_lines = "\n".join(_format_job_line(job) for job in jobs)

    # Total duration at the bottom (only when all jobs are done)
    total = _total_duration(jobs)
    footer = f"\n\n\u23f1 {total}" if total and overall != "in_progress" else ""

    return f"{header}{meta}\n{job_lines}{footer}"


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
