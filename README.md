# cerrrbot

**cerrrbot** is a Telegram Bot designed as a **"Smart Saved Messages"** hub. It collects, organizes, and automates content, media, and background tasks sennt or forwarded to the bot.

---

## Table of Contents

- [About](#about)
  - [Problem](#problem)
  - [Solution](#solution)
- [Technology Stack](#technology-stack)
- [Core Features](#core-features)
  - [Interactive Message Triage & Menus](#interactive-message-triage--menus)
  - [Automated Default Action Countdown](#automated-default-action-countdown)
  - [Media & File Management](#media--file-management)
  - [Notification Engine](#notification-engine)
  - [Background Task Queue & Interactive Control](#background-task-queue--interactive-control)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Clone the Repository](#clone-the-repository)
  - [Running Locally with uv](#running-locally-with-uv)
  - [Running with Docker Compose](#running-with-docker-compose)
- [Development & Makefile Commands](#development--makefile-commands)
  - [Polling Mode](#polling-mode)
  - [Webhook Mode & Local Telegram Bot API Server](#webhook-mode--local-telegram-bot-api-server)
- [Configuration Reference](#configuration-reference)
- [Bot Execution Modes](#bot-execution-modes)
- [Plugin System & Extensibility](#plugin-system--extensibility)
  - [Plugin Architecture](#plugin-architecture)
  - [Dependency Injection with Dishka](#dependency-injection-with-dishka)
  - [Custom Actions & Regex Matching](#custom-actions--regex-matching)
  - [Creating Your Own Plugin](#creating-your-own-plugin)

---

## About

### Problem
As Telegram serves as a primary hub for communication, news channels, memes, and media consumption, users frequently forward items to their **Saved Messages** chat. Over time, this chat becomes cluttered with an unorganized mixture of temporary notes, long-term bookmarks, and media files, making it hard to distinguish important information from temporary clutter.

### Solution
**cerrrbot** transforms the traditional Saved Messages flow into an automated, interactive inbox:
- Incoming messages are automatically parsed and paired with an **interactive action menu**.
- Content can be kept permanently, downloaded automatically, or set to auto-delete after a customizable timer.
- Heavy jobs are dispatched to a **Celery task queue** with real-time status updates and cancellation support in Telegram.
- A built-in **Redis notification scheduler** handles delayed and repeating reminders.
- A modular **plugin system** allows developers to easily extend functionality without modifying core bot code.

---

## Technology Stack

- **Runtime & Package Management**: Python 3.14+, [uv](https://github.com/astral-sh/uv) (fast package and workspace resolver)
- **Telegram Bot Framework**: [aiogram](https://github.com/aiogram/aiogram) 3.30+
- **Dependency Injection / IoC**: [Dishka](https://github.com/reagento/dishka) (scoped async container for clean architecture)
- **Distributed Task Queue**: [Celery](https://github.com/celery/celery) 5.6+
- **Databases & Caching**:
  - [MongoDB](https://www.mongodb.com/) 4.4+ (async message persistence with PyMongo)
  - [Redis](https://redis.io/) 8.0 (caching, notification priority queue, Celery broker/backend)
- **In-Process Scheduler**: [APScheduler](https://github.com/agronholm/apscheduler) 3.11+ (periodic task runner)
- **Configuration & Validation**: [Pydantic](https://docs.pydantic.dev/) v2 & [Pydantic-Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- **Logging**: [Loguru](https://github.com/Delgan/loguru) with formatted ASCII startup status tables
- **Containerization**: Docker & Docker Compose

---

## Core Features

### Interactive Message Triage & Menus
When a message or forward is sent to the bot, cerrrbot analyzes its content and responds with an inline keyboard menu:
- **`Keep`**: Moves the message to the permanent `saved_messages` collection and removes the menu.
- **`Delete`**: Opens a sub-menu to choose the deletion timing:
  - `Delete now`: Instantly deletes the message and reply from Telegram and MongoDB.
  - `Del in 15m` / `Del in 30m` / `Del in 45m`: Sets a delayed TTL for automatic removal.
- **`<- Back`**: Navigates back across multi-level dynamic inline menus.

### Automated Default Action Countdown
If no button is pressed within a configurable timeout (`CERRRBOT_TIMEOUT_BEFORE_DEFAULT_ACTION_PERFORMS`, default 10 seconds), the bot automatically executes the default content strategy (such as downloading media or setting a default deletion timer). Expired messages past their retention period are cleaned up by periodic background tasks.

### Media & File Management
cerrrbot handles all standard Telegram media types:
- **Supported Content Types**: Photos, videos, animations (GIFs), audio files, voice messages, video notes, documents, and stickers.
- **Single & Batch Downloads**: Messages with multiple media items (media groups) offer `Download` (first item) and `Download all` (entire group).
- **Sticker Packs**: When a sticker is sent, the bot can download the single sticker or the entire sticker pack by name.
- **Organized Storage**: Downloads are stored in monthly subdirectories (`YYYY-MM`) or named sticker pack folders.
- **Deterministic File Naming**: Files are saved with collision-free naming based on source and content hash:
  `{source_id}_{origin_date}_{file_unique_id_hash}.{ext}`
- **Large File Support (>50MB)**: When paired with a local Telegram Bot API server, files up to 2000MB are downloaded directly via high-speed local filesystem operations (`shutil.move`).

### Notification Engine
The bot includes a Redis-backed notification service for asynchronous and scheduled message delivery:
- **Scheduling**: Send notifications at specific UTC timestamps (`send_at`).
- **Repetition**: Supports recurring alerts with count and interval (`send_count`, `repeat_in`).
- **Context Linking**: Notifications can reply directly to original messages (`reply_to_message_id`).
- **Background Dispatcher**: APScheduler periodically inspects the Redis notification queue and dispatches due messages.

### Background Task Queue & Interactive Control
Long-running or heavy operations (such as media extraction or scraping) are offloaded to Celery workers:
- **`AsyncTask` abstraction**: Tasks inherit from `AbortableTask` and integrate with Dishka's async DI container.
- **Status Checks (`Show status`)**: Check the current Celery task state directly from Telegram inline buttons.
- **Task Abort (`Stop`)**: Cancel running tasks on demand via Telegram callback queries.

---

## Getting Started

### Prerequisites
- **Python 3.14+**
- **[uv](https://github.com/astral-sh/uv)** (recommended)
- **MongoDB 4.4+**
- **Redis 8.0+**
- **Docker & Docker Compose** *(optional, for containerized deployment)*

### Clone the Repository
```bash
git clone --recurse-submodules https://github.com/kehlerr/cerrrbot.git
cd cerrrbot
```

### Running Locally with uv

1. **Initialize environment and copy configuration template**:
   ```bash
   make init
   ```
   *(This creates the `appdata` directory and copies `sample.env` to `.env`)*

2. **Configure `.env`**:
   Open `.env` and set your `CERRRBOT_TOKEN` (from [@BotFather](https://t.me/BotFather)) and `CERRRBOT_ALLOWED_USERS` (your Telegram User ID):
   ```env
   CERRRBOT_TOKEN="1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ"
   CERRRBOT_ALLOWED_USERS="123456789"
   ```

3. **Install dependencies**:
   ```bash
   make sync
   ```

4. **Start the Celery worker** *(in a separate terminal)*:
   ```bash
   make celery
   ```

5. **Run the bot**:
   ```bash
   make run
   ```

### Running with Docker Compose

1. **Create the shared Docker network** *(first time only)*:
   ```bash
   docker network create cerrrbot-network
   ```

2. **Initialize configuration**:
   ```bash
   make init
   ```
   Configure `.env` with your bot token and allowed user IDs.

3. **Start all services** (MongoDB, Redis, Bot, Celery Worker, and Telegram API Server):
   ```bash
   make dc_up
   ```

4. **View logs**:
   ```bash
   make logs
   ```

---

## Development & Makefile Commands

The included `Makefile` provides convenient shortcuts for development, testing, and deployment:

| Command | Description |
| :--- | :--- |
| `make init` | Create `appdata/` directory and copy `sample.env` to `.env` |
| `make copy_env` | Copy `sample.env` to `.env` |
| `make sync` | Synchronize all dependencies and workspace members via `uv sync` |
| `make run` | Run the bot application locally with `uv run -m app` |
| `make celery` | Start the Celery worker locally with `uv run celery` |
| `make pretty` | Format code and auto-fix linting issues with Ruff |
| `make lint` | Run Ruff format check, Ruff linter, and MyPy type checks |
| `make dc_up` | Build and start all Docker containers in background |
| `make dc_stop` | Stop application Docker containers (`app-bot`, `app-celery-worker`) |
| `make dc_stop_all` | Stop all Docker containers (including Redis and MongoDB) |
| `make deploy` | Re-deploy containers (`dc_stop` -> `dc_rm` -> `dc_up`) |
| `make logs` | Stream logs for bot and Celery worker containers |
| `make clean` | Clean up temporary files, caches, and build artifacts |

---

## Configuration Reference

All settings can be specified in `.env` or passed as environment variables.

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| **`CERRRBOT_DEBUG`** | `bool` | `False` | Enable debug mode |
| **`CERRRBOT_LOGGING_LEVEL`** | `str` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| **`CERRRBOT_LOGGING_SCOPE`** | `str` | `all` | Logging scope: `app` (cerrrbot only) or `all` (includes libraries) |
| **`CERRRBOT_TIMEZONE`** | `str` | `UTC` | IANA timezone string (e.g. `UTC`, `Europe/London`, `America/New_York`) |
| **`CERRRBOT_TOKEN`** | `str` | *Required* | Telegram Bot API token from @BotFather |
| **`CERRRBOT_MODE`** | `str` | `polling` | Execution mode: `polling`, `webhook`, or `auto` |
| **`CERRRBOT_ALLOWED_USERS`** | `str` | *Required* | Comma-separated list of authorized Telegram User IDs |
| **`CERRRBOT_DATA_ROOT`** | `str` | `./appdata` | Base directory for storing downloaded media |
| **`CERRRBOT_MAX_LOAD_FILE_SIZE`** | `int` | `20000000` | Max file size in bytes for auto-downloads (`-1` for unlimited) |
| **`CERRRBOT_MESSAGE_TTL`** | `int` | `169200` | Message validity TTL in seconds (~47 hours) |
| **`CERRRBOT_DELETE_TIMEOUT_1`** | `int` | `15` | Delayed deletion option 1 (seconds) |
| **`CERRRBOT_DELETE_TIMEOUT_2`** | `int` | `30` | Delayed deletion option 2 (seconds) |
| **`CERRRBOT_DELETE_TIMEOUT_3`** | `int` | `45` | Delayed deletion option 3 (seconds) |
| **`CERRRBOT_TIMEOUT_BEFORE_DEFAULT_ACTION_PERFORMS`** | `int` | `10` | Seconds before executing default fallback action |
| **`CERRRBOT_CHECK_NEW_MESSAGES_CD_PERIOD`** | `int` | `3` | Scheduler interval to process pending default actions (seconds) |
| **`CERRRBOT_CHECK_DEPRECATED_MESSAGES_CD_PERIOD`** | `int` | `60` | Scheduler interval for expired messages cleanup (seconds) |
| **`CERRRBOT_CHECK_NOTIFICATIONS_CD_PERIOD`** | `int` | `10` | Scheduler interval for processing due notifications (seconds) |
| **`CERRRBOT_MONGO_DB_HOST`** | `str` | `localhost` | MongoDB host |
| **`CERRRBOT_MONGO_DB_PORT`** | `int` | `27017` | MongoDB port |
| **`CERRRBOT_MONGO_DB_NAME`** | `str` | `cerrrbot_mongo` | MongoDB database name |
| **`CERRRBOT_REDIS_HOST`** | `str` | `localhost` | Redis host |
| **`CERRRBOT_REDIS_PORT`** | `int` | `6379` | Redis port |
| **`CERRRBOT_REDIS_DB`** | `int` | `1` | Redis database index for general cache |
| **`CERRRBOT_NOTIFICATIONS_DB`** | `int` | `3` | Redis database index for notifications |
| **`CERRRBOT_CELERY_BROKER_DB`** | `int` | `0` | Redis database index for Celery broker |
| **`CERRRBOT_CELERY_BACKEND_DB`** | `int` | `1` | Redis database index for Celery result backend |
| **`CERRRBOT_TG_API_ID`** | `str` | `None` | Telegram API ID (for local TG API server) |
| **`CERRRBOT_TG_API_HASH`** | `str` | `None` | Telegram API Hash (for local TG API server) |
| **`CERRRBOT_TG_API_SERVER_HOST`** | `str` | `tg-api-server` | Local Telegram API server host |
| **`CERRRBOT_TG_API_SERVER_PORT`** | `int` | `8081` | Local Telegram API server port |
| **`CERRRBOT_WEBHOOK_HOST`** | `str` | `0.0.0.0` | Webhook HTTP server binding host |
| **`CERRRBOT_WEBHOOK_PORT`** | `int` | `8000` | Webhook HTTP server port |
| **`CERRRBOT_WEBHOOK_ENDPOINT`** | `str` | `/webhook` | Webhook URL path |
| **`CERRRBOT_WEBHOOK_SECRET`** | `str` | `None` | Webhook secret token for header verification |

---

## Bot Execution Modes

### Polling Mode
Configured via `CERRRBOT_MODE=polling`. The bot uses long-polling to fetch updates from Telegram servers. This is the simplest mode and requires no public IP, open ports, or SSL certificates.

### Webhook Mode & Local Telegram Bot API Server
Configured via `CERRRBOT_MODE=webhook`. In this mode, the bot runs an `aiohttp` web server and processes updates via webhooks.

When paired with a **local Telegram Bot API Server** (included in `docker/docker-compose-infra.yml`):
- **Bypasses the 50MB file size limit** for bot downloads (up to 2000MB).
- Downloads happen via direct local disk file transfers rather than HTTP streaming over the internet.
- Configure `CERRRBOT_TG_API_ID` and `CERRRBOT_TG_API_HASH` from [my.telegram.org](https://core.telegram.org/api/obtaining_api_id).

---

## Plugin System & Extensibility

cerrrbot features a modular architecture that makes extending the bot straightforward. Plugins can register custom message actions, Celery tasks, dependency injection providers, command routers, and startup hooks.

### Plugin Architecture
Each plugin is located in `app/plugins/<plugin_name>/` and managed by `PluginsManager`:

```
app/plugins/<plugin_name>/
├── __init__.py          # Exports the Plugin instance
├── settings.py          # Plugin-specific Pydantic settings
├── tasks.py             # Asynchronous / Celery tasks
├── commands.py          # (Optional) Aiogram command router
├── ioc.py               # (Optional) Dishka DI provider
└── handlers.py          # (Optional) Event handlers & startup hooks
```

### Dependency Injection with Dishka
Plugins can define their own `Provider` classes to inject custom services or repositories into bot handlers and Celery tasks using `@inject` and `FromDishka[ServiceType]`.

### Custom Actions & Regex Matching
Plugins can attach custom interactive inline buttons (`CustomMessageAction`) to messages:
- **`regex`**: Display the button only when message text matches a regular expression (or `*` for all messages).
- **`parse_links` / `allowed_hosts`**: Automatically extract matching URLs from the message and pass them to the task.
- **`is_instant`**: Run immediately in the bot event loop instead of dispatching to Celery.
- **`order`**: Control button sorting in the inline keyboard (`order >= 100`).

### Creating Your Own Plugin

Here is a minimal step-by-step example to create a new plugin named `sample_plugin`:

#### 1. Define Settings (`app/plugins/sample_plugin/settings.py`)
```python
from pydantic import Field
from app.plugins.base import PluginSettings


class SamplePluginSettings(PluginSettings):
    NAME = "SAMPLE"  # Reads SAMPLE_ENABLED, SAMPLE_API_KEY, etc. from .env

    api_key: str = Field(default="")
    max_items: int = Field(default=10)


settings = SamplePluginSettings()
```

#### 2. Define Tasks (`app/plugins/sample_plugin/tasks.py`)
```python
from typing import Any
from dishka.integrations.aiogram import FromDishka, inject
from app.models import ActionResult, CustomMessageAction
from app.notifications import Notification, NotificationService
from app.plugins.base import AsyncTask
from app.savmes import SavmesService


class SampleTask(AsyncTask):
    name = "SampleTask"

    # Define the button shown on matching messages
    action = CustomMessageAction(
        code="SMPL_ACT",
        caption="Process Item",
        order=700,
        executor_args={
            "task_name": name,
            "regex": r"#process",  # Show button if message contains '#process'
            "is_instant": False,  # Execute as a Celery background task
        },
    )

    @inject
    async def arun_impl(
        self,
        *args: Any,
        savmes_service: FromDishka[SavmesService],
        notification_service: FromDishka[NotificationService],
        msgdoc_id: str,
        **kwargs: Any,
    ) -> ActionResult:
        msgdoc = await savmes_service.get_msgdoc_by_id(msgdoc_id)
        if not msgdoc:
            return ActionResult(success=False)

        # Offloaded background business logic...

        # Send completion notification
        await notification_service.push_message_notification(
            Notification(
                text="Item processed successfully!",
                reply_to_message_id=msgdoc.message_id,
            )
        )
        return ActionResult(success=True)
```

#### 3. Export the Plugin (`app/plugins/sample_plugin/__init__.py`)
```python
from app.plugins.base import Plugin
from .settings import settings
from .tasks import SampleTask

plugin = Plugin(
    name="sample_plugin",
    settings=settings,
    tasks=(SampleTask,),
)

__all__ = ("plugin",)
```

Once placed in `app/plugins/`, the plugin is automatically discovered, verified, and loaded on bot startup.
