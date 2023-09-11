from message_action import CustomMessageAction

from .tasks import TelegraphScrapeTask


actions = (
    CustomMessageAction(code="TGHP_DL", caption="Telegraph DL", order=600, method_args={
        "task_name": "plugins.telegraph.tasks.TelegraphScrapeTask",
        "regex": r"(?P<url>https?:\/\/(www\.)?telegra.ph\/([a-zA-Z0-9-_]+)\/?)"
    }),
)

tasks = (
    TelegraphScrapeTask,
)