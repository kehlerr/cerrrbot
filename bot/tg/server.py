from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp.web import Application as AiohttpApp

from settings import WEBHOOK_ENDPOINT, WEBHOOK_SECRET


def create_webhook_server(bot: Bot, dispatcher: Dispatcher) -> AiohttpApp:
    # Create aiohttp.web.Application instance
    app = AiohttpApp()

    # Create an instance of Simple request handler
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dispatcher,
        bot=bot,
        secret_token=WEBHOOK_SECRET,
    )
    # Register webhook handler on application
    webhook_requests_handler.register(app, path=WEBHOOK_ENDPOINT)

    # Mount dispatcher startup and shutdown hooks to aiohttp application
    setup_application(app, dispatcher, bot=bot)

    return app
