from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.exceptions import InvalidSettingError


class BotModeType(StrEnum):
    AUTO = "auto"
    WEBHOOK = "webhook"
    POLLING = "polling"


class WebhookServerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CERRRBOT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    tg_api_server_scheme: str = Field(default="http")
    tg_api_server_host: str | None = Field(default=None)
    tg_api_server_port: int = Field(default=8081)

    webhook_scheme: str = Field(default="https")
    webhook_endpoint: str = Field(default="/webhook")
    webhook_secret: str
    webhook_host: str = Field(default="0.0.0.0")
    webhook_port: int = Field(default=8000)

    @property
    def bot_api_server_uri(self) -> str:
        return f"{self.tg_api_server_scheme}://{self.tg_api_server_host}:{self.tg_api_server_port}"

    @property
    def webhook_endpoint_url(self) -> str:
        return f"{self.webhook_scheme}://{self.webhook_host}:{self.webhook_port}{self.webhook_endpoint}"

    @model_validator(mode="after")
    def validate_webhook_settings(self) -> Self:
        missing = []

        if not self.tg_api_server_scheme:
            missing.append("CERRRBOT_BOT_API_SERVER_SCHEME")

        if not self.tg_api_server_host:
            missing.append("CERRRBOT_BOT_API_SERVER_HOST")

        if not self.webhook_secret:
            missing.append("CERRRBOT_WEBHOOK_SECRET")

        if not self.webhook_scheme:
            missing.append("CERRRBOT_WEBHOOK_SCHEME")

        if not self.webhook_host:
            missing.append("CERRRBOT_WEBHOOK_HOST")

        if not self.webhook_endpoint:
            missing.append("CERRRBOT_WEBHOOK_ENDPOINT")

        if missing:
            raise InvalidSettingError(
                f"Bot mode is set to '{BotModeType.WEBHOOK}', but missing required setting(s): {', '.join(missing)}"
            )
        return self


class CerrrBotSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CERRRBOT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Bot TG-related settings
    token: str = Field(validation_alias="CERRRBOT_TOKEN")

    # Bot execution mode
    mode: BotModeType = Field(default=BotModeType.AUTO)

    # Webhook & bot server settings (only initialized when bot_mode is webhook)
    webhook: WebhookServerSettings | None = None


cerrrbot_settings = CerrrBotSettings()  # type: ignore[call-arg]
