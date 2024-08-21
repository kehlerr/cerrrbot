import logging
import shutil

from pathlib import Path
from typing import Any, BinaryIO, cast, Self

from aiogram import Bot as AiogramBot, Dispatcher, Router
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer

from commands import load_commands
from common import CheckUserMiddleware
from settings import BOT_TOKEN, BOT_API_SERVER_URI, WEBHOOK_ENDPOINT_URL, WEBHOOK_SECRET
from services import savmes
from services.background_tasks import create_background_tasks

from .server import create_webhook_server

logger = logging.getLogger(__name__)



class CustomBot(AiogramBot):
    async def download_file(
        self,
        file_path: str,
        *args: Any,
        destination: BinaryIO | Path | str | None = None,
        **kwargs: Any
    ) -> BinaryIO | None:
        if not self.session.api.is_local or not (destination := cast(str, destination)):
            return await super().download_file(file_path,  destination, *args, **kwargs)

        Path(destination).parent.mkdir(parents=True, exist_ok=True)

        return shutil.move(file_path, destination)

    @classmethod
    def create(cls) -> Self:
        logger.info("Creating local server...")
        api_server = TelegramAPIServer.from_base(BOT_API_SERVER_URI, is_local=True)

        logger.info("Creating session for local server...")
        session = AiohttpSession(api=api_server)

        logger.info("Starting bot...")
        return cls(token=BOT_TOKEN, session=session)

    def setup(self) -> None:
        router = self.create_router()
        dispatcher = self.create_dispatcher(router)
        self.web_app = create_webhook_server(self, dispatcher)

    def create_router(self) -> Router:
        main_router = Router()
        main_router.message.middleware(CheckUserMiddleware())

        load_commands(main_router)
        main_router.include_router(savmes.router)

        return main_router

    def create_dispatcher(self, main_router: Router) -> Dispatcher:
        dispatcher = Dispatcher()
        dispatcher.include_router(main_router)

        # Register startup hook to initialize webhook
        dispatcher.startup.register(self.on_startup)

        return dispatcher

    async def on_startup(self) -> None:
        await self.delete_webhook()
        await self.set_webhook(WEBHOOK_ENDPOINT_URL, secret_token=WEBHOOK_SECRET)
        await create_background_tasks(self)

    async def logout(self) -> None:
        """Run this func before starting local server at first time."""
        result = await self.log_out()
        if result:
            exit(0)