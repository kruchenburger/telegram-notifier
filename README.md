# Telegram Notifier

GitHub Action для отправки уведомлений о статусе CI/CD пайплайнов в Telegram.

Поддерживает два режима:

- **Legacy** — одно сообщение со статусом job
- **Pipeline** (v2) — живой трекинг всех jobs с автообновлением

## Подготовка

1. Зарегистрируйте бота через [@BotFather](https://t.me/botfather) и получите токен. [Инструкция](https://core.telegram.org/bots/features#creating-a-new-bot)
2. Получите `chat_id` через [@username_to_id_bot](https://t.me/username_to_id_bot)
3. Для отправки в канал или группу — добавьте бота туда

## Legacy режим

Простое уведомление со статусом одного job:

```yaml
- name: Telegram Notification
  if: always()
  uses: kruchenburger/telegram-notifier@v2
  with:
    status: ${{ job.status }}
    token: ${{ secrets.TG_TOKEN }}
    chat_id: ${{ secrets.TG_CHAT_ID }}
```

## Pipeline режим

Один tracker job стартует параллельно с остальными, опрашивает GitHub API и обновляет одно Telegram-сообщение по мере завершения каждого job:

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

Результат в Telegram обновляется в реальном времени:

```
🟡 CI/CD
Repo: org/repo
Branch: main
Commit: abc1234

  ✅ Lint  23s
  🔄 Test
  ⏳ Build
  ⏳ Deploy
```

### Inputs

| Input          | Описание                                            | Обязателен       |
| -------------- | --------------------------------------------------- | ---------------- |
| `token`        | Telegram API токен бота                             | Да               |
| `chat_id`      | ID чата или `@channel_name`                         | Да               |
| `status`       | Статус job (legacy режим)                           | Legacy режим     |
| `pipeline`     | Включить pipeline трекинг (`true`/`false`)          | Нет (`false`)    |
| `github-token` | GitHub token для доступа к API                      | Pipeline режим   |
| `exclude-jobs` | Паттерны имён jobs для исключения (через запятую)   | Нет              |
| `poll-interval` | Интервал опроса в секундах                         | Нет (`15`)       |

### Outputs

| Output       | Описание                      |
| ------------ | ----------------------------- |
| `status`     | Статус доставки               |
| `message_id` | ID Telegram-сообщения         |
