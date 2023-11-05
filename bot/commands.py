from aiogram import Router, types
from aiogram.filters import Command

commands_router = Router()


@commands_router.message(Command(commands=["start", "menu"]))
async def main_menu(message: types.Message) -> None:
    await message.answer("Welcome, master")


def load_commands(main_router: Router) -> None:
    from plugins_manager import plugins_manager
    for plugin_commands_router in plugins_manager.get_commands_routers():
        commands_router.include_router(plugin_commands_router)
    main_router.include_router(commands_router)