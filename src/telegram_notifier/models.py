from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class JobInfo:
    """Represents a single job from a GitHub Actions workflow run."""

    name: str
    status: str  # "queued" | "in_progress" | "completed"
    conclusion: str | None  # "success" | "failure" | "cancelled" | "skipped" | None
    started_at: datetime | None
    completed_at: datetime | None


@dataclass(frozen=True, slots=True)
class WorkflowContext:
    """GitHub context information from environment variables."""

    server_url: str
    repository: str
    workflow_name: str
    ref: str
    sha: str
    run_id: str
    actor: str
    event_name: str
    pr_title: str | None = None
    pr_number: str | None = None

    @property
    def repo_url(self) -> str:
        return f"{self.server_url}/{self.repository}"

    @property
    def workflow_url(self) -> str:
        return f"{self.repo_url}/actions/runs/{self.run_id}"

    @property
    def ref_url(self) -> str:
        return f"{self.repo_url}/tree/{self.ref}"

    @property
    def commit_url(self) -> str:
        return f"{self.repo_url}/commit/{self.sha}"

    @property
    def pr_url(self) -> str | None:
        if self.pr_number is None:
            return None
        return f"{self.repo_url}/pull/{self.pr_number}"
