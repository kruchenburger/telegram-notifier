import asyncio
import logging
import os

from telegram_notifier.github_api import fetch_workflow_jobs, filter_jobs
from telegram_notifier.message_builder import (
    build_legacy_message,
    build_pipeline_message,
    determine_overall_status,
)
from telegram_notifier.models import JobInfo, WorkflowContext
from telegram_notifier.telegram import edit_message, send_message

logger = logging.getLogger(__name__)

_DEFAULT_POLL_INTERVAL = 15
_INITIAL_DELAY = 5
_MAX_POLL_DURATION = 60 * 60  # 60 minutes


def set_action_output(output_name: str, output_value: str) -> None:
    """Writes a GitHub Action output variable to the GITHUB_OUTPUT file."""
    github_output_file = os.path.abspath(os.environ["GITHUB_OUTPUT"])
    with open(github_output_file, "a", encoding="UTF-8") as f:
        f.write(f"{output_name}={output_value}\n")


def _get_workflow_context() -> WorkflowContext:
    """Build WorkflowContext from GitHub environment variables."""
    return WorkflowContext(
        server_url=os.getenv("GITHUB_SERVER_URL", ""),
        repository=os.getenv("GITHUB_REPOSITORY", ""),
        workflow_name=os.getenv("GITHUB_WORKFLOW", ""),
        ref=os.getenv("GITHUB_REF_NAME", ""),
        sha=os.getenv("GITHUB_SHA", ""),
        run_id=os.getenv("GITHUB_RUN_ID", ""),
    )


async def _run_legacy_mode(
    token: str,
    chat_id: str,
    status: str,
    ctx: WorkflowContext,
) -> None:
    """Original v1 behavior: send a single notification message."""
    message = build_legacy_message(
        github_url=ctx.server_url,
        repo_name=ctx.repository,
        workflow_name=ctx.workflow_name,
        ref=ctx.ref,
        commit=ctx.sha,
        run_id=ctx.run_id,
        status=status,
    )
    try:
        msg_id = await send_message(token, chat_id, message)
        set_action_output("status", "Successfully delivered")
        set_action_output("message_id", str(msg_id))
    except Exception:
        set_action_output("status", "Notification has not been delivered")
        logger.exception("Failed to send notification")
        raise


async def _run_pipeline_mode(
    token: str,
    chat_id: str,
    github_token: str,
    ctx: WorkflowContext,
    exclude_patterns: list[str],
    poll_interval: int,
) -> None:
    """Pipeline progress mode: poll GitHub API and update Telegram message."""
    # Initial delay to let other jobs appear in the API
    await asyncio.sleep(_INITIAL_DELAY)

    all_jobs = await fetch_workflow_jobs(
        github_token=github_token,
        repository=ctx.repository,
        run_id=ctx.run_id,
    )
    filtered = filter_jobs(all_jobs, exclude_patterns)
    current_text = build_pipeline_message(ctx, filtered)

    # Send initial message
    msg_id = await send_message(token, chat_id, current_text)
    set_action_output("message_id", str(msg_id))
    logger.info("Sent initial pipeline message (message_id=%d)", msg_id)

    # Check if already done
    if _all_completed(filtered):
        set_action_output("status", "Successfully delivered")
        return

    # Polling loop
    elapsed = 0
    while elapsed < _MAX_POLL_DURATION:
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

        all_jobs = await fetch_workflow_jobs(
            github_token=github_token,
            repository=ctx.repository,
            run_id=ctx.run_id,
        )
        filtered = filter_jobs(all_jobs, exclude_patterns)
        new_text = build_pipeline_message(ctx, filtered)

        if new_text != current_text:
            await edit_message(token, chat_id, msg_id, new_text)
            current_text = new_text
            logger.info("Updated pipeline message")

        if _all_completed(filtered):
            break

    overall = determine_overall_status(filtered)
    set_action_output("status", f"Pipeline {overall}")


def _all_completed(jobs: list[JobInfo]) -> bool:
    """Check if all jobs have completed."""
    return bool(jobs) and all(j.status == "completed" for j in jobs)


async def main() -> None:
    """Main entry point: route between legacy and pipeline modes."""
    token = os.getenv("INPUT_TOKEN")
    chat_id = os.getenv("INPUT_CHAT_ID")

    if token is None:
        raise KeyError("Telegram token is required")
    if chat_id is None:
        raise KeyError("Telegram chat_id is required")

    ctx = _get_workflow_context()

    pipeline_mode = os.getenv("INPUT_PIPELINE", "false").lower() == "true"

    if pipeline_mode:
        github_token = os.getenv("INPUT_GITHUB-TOKEN")
        if github_token is None:
            raise KeyError("github-token is required when pipeline=true")

        exclude_raw = os.getenv("INPUT_EXCLUDE-JOBS", "")
        exclude_patterns = [p for p in exclude_raw.split(",") if p.strip()]

        poll_interval = int(
            os.getenv("INPUT_POLL-INTERVAL", str(_DEFAULT_POLL_INTERVAL))
        )

        await _run_pipeline_mode(
            token=token,
            chat_id=chat_id,
            github_token=github_token,
            ctx=ctx,
            exclude_patterns=exclude_patterns,
            poll_interval=poll_interval,
        )
    else:
        status = os.getenv("INPUT_STATUS")
        if status is None:
            raise KeyError("status is required when pipeline mode is disabled")
        await _run_legacy_mode(token, chat_id, status, ctx)


if __name__ == "__main__":
    asyncio.run(main())
