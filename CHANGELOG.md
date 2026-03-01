# Changelog

## [2.0.0] - 2026-03-01

### Added

- Pipeline tracking mode: live progress updates for all workflow jobs in a single Telegram message
- GitHub API integration for automatic job discovery and status polling
- New inputs: `pipeline`, `github-token`, `exclude-jobs`, `poll-interval`
- New output: `message_id` (Telegram message ID)
- Telegram message editing via `editMessageText` for live updates
- PR title display: for pull request events, shows PR title instead of branch name
- Commit author display in pipeline messages
- Total pipeline duration shown when all jobs complete
- Skipped jobs displayed without duration
- Spinner icon for in-progress pipeline (instead of yellow circle)
- Modular code architecture: `models`, `telegram`, `message_builder`, `github_api`

### Changed

- `status` input is now optional (required only in legacy mode)
- Migrated to uv (pyproject.toml + uv.lock)
- Restructured project to `src/telegram_notifier/` layout
- Dockerfile: multi-stage build with uv instead of pip + distroless
- CI: added lint (ruff) and test (pytest) jobs

## [1.0.0] - 2025-05-08

Initial release.

### Added

- Docker-based GitHub Action for sending CI/CD pipeline status notifications to Telegram
- HTML-formatted messages with links to repository, workflow, branch, and commit
- Status emoji mapping: success, failure, cancelled
- GitHub Action output with delivery status
- Self-test CI workflow
