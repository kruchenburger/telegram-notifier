# Telegram Notifier

GitHub Action for sending CI/CD pipeline status notifications to Telegram.

Supports two modes:

- **Legacy** — single message with job status
- **Pipeline** (v2) — live tracking of all jobs with auto-updating message

## Setup

1. Create a bot via [@BotFather](https://t.me/botfather) and get the token. [Guide](https://core.telegram.org/bots/features#creating-a-new-bot)
2. Get your `chat_id` via [@username_to_id_bot](https://t.me/username_to_id_bot)
3. To send to a channel or group — add the bot there

## Legacy mode

Simple notification with a single job status:

```yaml
- name: Telegram Notification
  if: always()
  uses: kruchenburger/telegram-notifier@v2
  with:
    status: ${{ job.status }}
    token: ${{ secrets.TG_TOKEN }}
    chat_id: ${{ secrets.TG_CHAT_ID }}
```

## Pipeline mode

A single tracker job starts in parallel with the rest, polls the GitHub API, and updates one Telegram message as each job completes.

The `github-token` requires `actions: read` permission. The default `GITHUB_TOKEN` works — just add the permission to the tracker job:

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
          token: ${{ secrets.TG_TOKEN }}
          chat_id: ${{ secrets.TG_CHAT_ID }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
          pipeline: true
          exclude-jobs: tracker

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm run lint

  test:
    needs: [lint]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm test

  build:
    needs: [test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm run build

  deploy:
    needs: [build]
    runs-on: ubuntu-latest
    steps:
      - run: echo "deploying..."
```

The Telegram message updates in real time:

```
🔄 CI/CD
Repo: org/repo
PR: Add new feature
Commit: abc1234
Author: username

  ✅ Lint  23s
  🔄 Test
  ⏳ Build
  ⏳ Deploy
```

When all jobs complete, a total duration and final status icon appear:

```
🟢 CI/CD
Repo: org/repo
Branch: main
Commit: abc1234
Author: username

  ✅ Lint  23s
  ✅ Test  1m 42s
  ✅ Build  3m 12s
  ⏭️ Deploy

⏱ 3m 35s
```

For pull requests, the PR title is shown instead of the branch name. Skipped jobs are displayed without duration.

### Inputs

| Input          | Description                                         | Required         |
| -------------- | --------------------------------------------------- | ---------------- |
| `token`        | Telegram Bot API token                              | Yes              |
| `chat_id`      | Chat ID or `@channel_name`                          | Yes              |
| `status`       | Job status (legacy mode)                            | Legacy mode      |
| `pipeline`     | Enable pipeline tracking (`true`/`false`)           | No (`false`)     |
| `github-token` | GitHub token for API access                         | Pipeline mode    |
| `exclude-jobs` | Comma-separated job name patterns to exclude        | No               |
| `poll-interval` | Polling interval in seconds                        | No (`15`)        |

### Outputs

| Output       | Description                   |
| ------------ | ----------------------------- |
| `status`     | Delivery status               |
| `message_id` | Telegram message ID           |
