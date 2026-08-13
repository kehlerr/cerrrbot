from aiogram.filters.callback_data import CallbackData


class ActionCallbackData(CallbackData, prefix="SVM"):
    action: str
    msgdoc_id: str
