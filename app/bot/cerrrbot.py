import asyncio
import shutil
from pathlib import Path
from typing import Any, BinaryIO, Self, cast

from aiogram import Bot as AiogramBot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.session.base import BaseSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from aiohttp.web import Application as AiohttpApp
from loguru import logger

from .settings import BotModeType, WebhookServerSettings, cerrrbot_settings


class CerrrBot(AiogramBot):
    _webhook_server_settings: WebhookServerSettings

    def __init__(
        self,
        token: str,
        session: BaseSession | None = None,
        default: DefaultBotProperties | None = None,
        webhook_server_settings: WebhookServerSettings | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(token, session, default, **kwargs)

        if webhook_server_settings:
            self._webhook_server_settings = webhook_server_settings

    @classmethod
    def create(cls) -> Self:

        if cerrrbot_settings.mode == BotModeType.WEBHOOK:
            webhook_server_settings = WebhookServerSettings()  # type: ignore

            logger.info(f"Configuring local Telegram API server session ({webhook_server_settings.bot_api_server_uri})...")
            api_server = TelegramAPIServer.from_base(webhook_server_settings.bot_api_server_uri, is_local=True)
            session = AiohttpSession(api=api_server)
        else:
            session = None
            webhook_server_settings = None

        logger.info(f"Initializing CerrrBot in '{cerrrbot_settings.mode}' mode...")
        return cls(token=cerrrbot_settings.token, session=session, webhook_server_settings=webhook_server_settings)

    async def download_file(
        self,
        file_path: str | Path,
        destination: BinaryIO | Path | str | None = None,
        timeout: int = 30,
        chunk_size: int = 65536,
        seek: bool = True,
    ) -> BinaryIO | None:
        if not self.session.api.is_local or not (destination := cast(str, destination)):
            return await super().download_file(file_path, destination, timeout, chunk_size, seek)

        Path(destination).parent.mkdir(parents=True, exist_ok=True)

        return shutil.move(file_path, destination)  # type: ignore

    async def start(self, dp: Dispatcher) -> None:
        if cerrrbot_settings.mode == BotModeType.WEBHOOK:
            await self._start_webhook_server(dp)
        else:
            await self._start_polling(dp)

    async def _start_polling(self, dp: Dispatcher) -> None:
        logger.info("Bot set up. Start polling...")
        await self.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(self)

    async def _start_webhook_server(self, dp: Dispatcher) -> None:
        host, port = self._webhook_server_settings.webhook_host, self._webhook_server_settings.webhook_port
        logger.info(f"Bot set up. Starting webhook server on {host}:{port}...")
        dp.startup.register(self._on_webhook_startup)

        web_app = self._create_webhook_server(dp)
        runner = web.AppRunner(web_app)
        await runner.setup()
        site = web.TCPSite(
            runner, host=self._webhook_server_settings.webhook_host, port=self._webhook_server_settings.webhook_port
        )
        await site.start()

        await asyncio.Event().wait()

    async def _on_webhook_startup(self) -> None:
        logger.info(f"Setting webhook to {self._webhook_server_settings.webhook_endpoint_url}...")
        await self.delete_webhook()
        await self.set_webhook(
            self._webhook_server_settings.webhook_endpoint_url, secret_token=self._webhook_server_settings.webhook_secret
        )

    async def logout(self) -> None:
        """Run this func before starting local server at first time."""
        result = await self.log_out()
        if result:
            exit(0)

    def _create_webhook_server(self, dispatcher: Dispatcher) -> AiohttpApp:
        # Create aiohttp.web.Application instance
        app = AiohttpApp()

        # Create an instance of Simple request handler
        webhook_requests_handler = SimpleRequestHandler(
            dispatcher=dispatcher,
            bot=self,
            secret_token=self._webhook_server_settings.webhook_secret,
        )
        # Register webhook handler on application
        webhook_requests_handler.register(app, path=self._webhook_server_settings.webhook_endpoint)

        # Mount dispatcher startup and shutdown hooks to aiohttp application
        setup_application(app, dispatcher, bot=self)

        return app
