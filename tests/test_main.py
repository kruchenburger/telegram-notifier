import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from telegram_notifier import main
from telegram_notifier.main import set_action_output
from telegram_notifier.models import JobInfo, WorkflowContext


def test_set_action_output_writes_to_file() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        temp_path = f.name

    try:
        os.environ["GITHUB_OUTPUT"] = temp_path
        set_action_output("status", "Successfully delivered")

        with open(temp_path, encoding="UTF-8") as f:
            content = f.read()

        assert content == "status=Successfully delivered\n"
    finally:
        os.unlink(temp_path)
        del os.environ["GITHUB_OUTPUT"]


def test_set_action_output_multiple_outputs() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        temp_path = f.name

    try:
        os.environ["GITHUB_OUTPUT"] = temp_path
        set_action_output("status", "ok")
        set_action_output("message_id", "12345")

        with open(temp_path, encoding="UTF-8") as f:
            content = f.read()

        assert content == "status=ok\nmessage_id=12345\n"
    finally:
        os.unlink(temp_path)
        del os.environ["GITHUB_OUTPUT"]


def _job(name: str, status: str = "completed") -> JobInfo:
    conclusion = "success" if status == "completed" else None
    return JobInfo(name, status, conclusion, None, None)


async def _run_pipeline(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, polls: list[list[JobInfo]]
) -> tuple[AsyncMock, AsyncMock]:
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "output"))
    monkeypatch.setattr(main.asyncio, "sleep", AsyncMock())
    fetch = AsyncMock(side_effect=polls)
    edit = AsyncMock()
    monkeypatch.setattr(main, "fetch_workflow_jobs", fetch)
    monkeypatch.setattr(main, "send_message", AsyncMock(return_value=1))
    monkeypatch.setattr(main, "edit_message", edit)
    ctx = WorkflowContext(
        "https://github.com", "o/r", "Release", "v1", "abc", "1", "a", "push"
    )
    await main._run_pipeline_mode("t", "c", "g", ctx, [], 15)
    return fetch, edit


async def test_pipeline_waits_for_a_chained_job_after_visible_jobs_finish(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    done = [_job("Deploy Backend")]
    both = [*done, _job("Deploy Webapp")]
    polls = [
        done,
        done,
        [*done, _job("Deploy Webapp", "queued")],
        both,
        both,
        both,
        both,
    ]

    fetch, edit = await _run_pipeline(monkeypatch, tmp_path, polls)

    assert fetch.await_count == len(polls)
    assert "Deploy Webapp" in edit.await_args.args[3]


async def test_pipeline_stops_after_the_grace_with_no_new_jobs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    done = [_job("Build")]
    polls = [done] * (1 + main._COMPLETION_GRACE // 15)

    fetch, _ = await _run_pipeline(monkeypatch, tmp_path, polls)

    assert fetch.await_count == len(polls)
