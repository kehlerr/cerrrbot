import os
from enum import StrEnum
from pathlib import Path
from typing import Any, Self

from pydantic import Field, field_validator, model_validator

from app.exceptions import InvalidSettingError
from app.types import CerrrBotSettings


class BotMode(StrEnum):
    AUTO = "auto"
    WEBHOOK = "webhook"
    POLLING = "polling"


class AppSettings(CerrrBotSettings):
    # Base app settings
    debug: bool = Field(default=False)
    logging_level: str = Field(default="DEBUG" if debug else "INFO")

    max_load_file_size: int = Field(default=20_000_000)
    message_ttl: int = Field(default=48 * 60 * 60 - 60 * 60)  # bot cannot operate with message that sent more than 48h ago

    # Bot app-related settings
    allowed_users: tuple[int, ...] = Field(default_factory=tuple)
    data_root: str = Field(default_factory=lambda: os.path.join(os.getcwd(), "appdata"))
    custom_message_min_order: int = 100

    # Timeouts
    delete_timeout_1: int = 15
    delete_timeout_2: int = 30
    delete_timeout_3: int = 45
    timeout_before_default_action_performs: int = 10
    check_new_messages_cd_period: int = 3
    check_deprecated_messages_cd_period: int = 60

    # Default cache settings
    cache_default_key_prefix: str = "cerrrbot_cache"

    # Notifications settings
    notifications_db: int = 3
    notifications_cache_key_prefix: str = "cerrrbot_notification"
    check_notifications_cd_period: int = 10

    @field_validator("allowed_users", mode="before")
    @classmethod
    def parse_allowed_users(cls, v: Any) -> tuple[int, ...]:
        if not v:
            return tuple()

        if isinstance(v, str):
            v_clean = v.strip("\"' ")
            return tuple(int(s.strip()) for s in v_clean.split(",") if s.strip())

        if isinstance(v, (list, tuple, set)):
            return tuple(int(x) for x in v)

        if isinstance(v, int):
            return (v,)

        raise InvalidSettingError(f"Invalid value for allowed users: {v}")

    @model_validator(mode="after")
    def compute_defaults_and_validate_paths(self) -> Self:
        if not self.logging_level:
            self.logging_level = "DEBUG" if self.debug else "INFO"
        else:
            self.logging_level = self.logging_level.upper()

        if not os.path.isdir(self.data_root):
            raise InvalidSettingError(f"CERRRBOT_DATA_ROOT doesn't exists: {self.data_root}")

        plugins_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "plugins")
        if not os.path.isdir(plugins_dir):
            raise InvalidSettingError(f"PLUGINS_DIR_PATH doesn't exists: {plugins_dir}")

        return self

    @property
    def main_user_chat(self) -> int:
        return self.allowed_users[0]


app_settings = AppSettings()  # type: ignore[call-arg]

PLUGINS_MODULE_NAME = "plugins"
PLUGINS_DIR_PATH = Path(__file__).relative_to(Path.cwd()).parent / PLUGINS_MODULE_NAME