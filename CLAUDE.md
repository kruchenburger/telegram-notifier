# telegram-notifier

GitHub Action (Docker-based) для отправки статусов CI/CD пайплайнов в Telegram.

## Стек

- **Python** 3.13+
- **python-telegram-bot** (PTB) для отправки/редактирования сообщений
- **httpx** для запросов к GitHub REST API
- **uv** как package manager
- **Docker** (multi-stage build с uv)

## Структура

```
telegram-notifier/
├── src/
│   └── telegram_notifier/
│       ├── __init__.py
│       ├── main.py              # Entrypoint: маршрутизация legacy/pipeline
│       ├── models.py            # Dataclasses: JobInfo, WorkflowContext
│       ├── telegram.py          # send_message(), edit_message()
│       ├── message_builder.py   # Построение HTML-сообщений
│       └── github_api.py        # GitHub REST API клиент
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

## Команды

```bash
uv sync                          # Установить зависимости
uv run ruff check .              # Линтер
uv run ruff format --check .     # Проверка форматирования
uv run ruff format .             # Автоформатирование
uv run pyright                   # Type checker
uv run pytest                    # Тесты
```

## Режимы работы

### Legacy (v1)

- Inputs: `token`, `chat_id`, `status`
- Отправляет одно сообщение со статусом job

### Pipeline (v2)

- Inputs: `token`, `chat_id`, `github-token`, `pipeline=true`
- Tracker job стартует параллельно с остальными
- Опрашивает GitHub API каждые N секунд
- Обновляет одно Telegram-сообщение по мере завершения jobs
- Завершается когда все jobs completed
