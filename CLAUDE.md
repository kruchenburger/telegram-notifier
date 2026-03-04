# telegram-notifier

Docker-based GitHub Action for sending CI/CD pipeline statuses to Telegram.

## Stack

- **Python** 3.13+
- **python-telegram-bot** (PTB) for sending/editing messages
- **httpx** for GitHub REST API requests
- **uv** as package manager
- **Docker** (multi-stage build with uv)

## Structure

```
telegram-notifier/
├── src/
│   └── telegram_notifier/
│       ├── __init__.py
│       ├── main.py              # Entrypoint: legacy/pipeline routing
│       ├── models.py            # Dataclasses: JobInfo, WorkflowContext
│       ├── telegram.py          # send_message(), edit_message()
│       ├── message_builder.py   # HTML message construction
│       └── github_api.py        # GitHub REST API client
├── tests/
│   ├── test_main.py
│   ├── test_message_builder.py
│   └── test_github_api.py
├── .github/
│   └── workflows/
│       └── selftest.yaml
├── action.yaml
├── Dockerfile
├── pyproject.toml
└── uv.lock
```

## Commands

```bash
uv sync                          # Install dependencies
uv run ruff check .              # Linter
uv run ruff format --check .     # Check formatting
uv run ruff format .             # Auto-format
uv run pyright                   # Type checker
uv run pytest                    # Tests
```

## Modes

### Legacy (v1)

- Inputs: `token`, `chat_id`, `status`
- Sends a single message with job status

### Pipeline (v2)

- Inputs: `token`, `chat_id`, `github-token`, `pipeline=true`
- Tracker job starts in parallel with other jobs
- Polls GitHub API every N seconds
- Updates a single Telegram message as jobs complete
- Finishes when all jobs are completed

## Action Inputs / Outputs

### Inputs

| Input           | Required | Default | Description                                                |
| --------------- | -------- | ------- | ---------------------------------------------------------- |
| `token`         | Yes      | —       | Telegram Bot token                                         |
| `chat_id`       | Yes      | —       | Chat ID or @channel_name                                   |
| `status`        | No       | —       | Job status (legacy mode only)                              |
| `pipeline`      | No       | `false` | Enable pipeline tracking mode                              |
| `github-token`  | No       | —       | GitHub token for workflow jobs (required if pipeline=true) |
| `exclude-jobs`  | No       | `""`    | Comma-separated job name patterns to exclude               |
| `poll-interval` | No       | `15`    | Polling interval in seconds (pipeline mode)                |

### Outputs

| Output       | Description                    |
| ------------ | ------------------------------ |
| `status`     | Status of the message delivery |
| `message_id` | Telegram message ID            |

## Usage Example

```yaml
jobs:
  tracker:
    runs-on: ubuntu-latest
    permissions:
      actions: read
    steps:
      - uses: kruchenburger/telegram-notifier@v2
        continue-on-error: true
        with:
          token: ${{ secrets.TG_NTF_TOKEN }}
          chat_id: ${{ secrets.TG_NTF_CHAT_ID }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
          pipeline: true
          exclude-jobs: tracker
```
