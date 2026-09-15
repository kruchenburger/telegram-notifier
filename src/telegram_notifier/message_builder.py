from __future__ import annotations

from datetime import datetime
from html import escape

from telegram_notifier.models import JobInfo, WorkflowContext

_JOB_ICONS: dict[str | None, str] = {
    "success": "\u2705",
    "failure": "\u274c",
    "cancelled": "\u26aa\ufe0f",
    "skipped": "\u2796",
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


def _link(url: str, text: str) -> str:
    """Render an HTML link with both the URL and the label escaped.

    Every value here ultimately comes from the workflow or GitHub context
    (job names, branch names, PR titles, actor) and may contain <, >, & or
    quotes; unescaped they make Telegram reject the whole message with
    "Can't parse entities".
    """
    return f'<a href="{escape(url, quote=True)}">{escape(text)}</a>'


def _format_job_line(job: JobInfo) -> str:
    """Format a single job as one line of the message."""
    icon = _job_icon(job)
    # Job names come from user workflows and may contain <, > or & — escape them,
    # otherwise Telegram rejects the message with "Can't parse entities".
    name = escape(job.name)
    # Don't show duration for skipped/cancelled jobs — they didn't really run
    if job.conclusion in ("skipped", "cancelled"):
        return f"  {icon} {name}"
    duration = _format_duration(job.started_at, job.completed_at)
    duration_part = f"  <i>{duration}</i>" if duration else ""
    return f"  {icon} {name}{duration_part}"


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

    header = f"{icon} <b>{_link(ctx.workflow_url, ctx.workflow_name)}</b>\n"

    # Show PR title if available, otherwise branch
    if ctx.pr_title is not None and ctx.pr_url is not None:
        ref_line = f"<b>PR:</b> {_link(ctx.pr_url, ctx.pr_title)}\n"
    else:
        ref_line = f"<b>Branch:</b> {_link(ctx.ref_url, ctx.ref)}\n"

    meta = (
        f"<b>Repo:</b> {_link(ctx.repo_url, ctx.repository)}\n"
        f"{ref_line}"
        f"<b>Commit:</b> {_link(ctx.commit_url, ctx.sha[:7])}\n"
        f"<b>Author:</b> {_link(f'{ctx.server_url}/{ctx.actor}', ctx.actor)}\n"
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
        f"<b>Repository:</b> {_link(repo_url, repo_name)}\n"
        f"<b>Workflow:</b> {_link(workflow_url, workflow_name)}\n"
        f"<b>Branch:</b> {_link(ref_url, ref)}\n"
        f"<b>Commit:</b> {_link(commit_url, commit[:7])}\n"
        f"<b>Status:</b> {escape(status)} {status_icon}"
    )
