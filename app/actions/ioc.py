from collections.abc import Iterable

from dishka import Provider, Scope, provide

from .action_executors import ActionExecutor, ActionExecutorRegistry


class ActionsProvider(Provider):
    def __init__(self, action_classes: Iterable[type[ActionExecutor]]) -> None:
        super().__init__()

        self._action_classes = action_classes

    @provide(scope=Scope.APP)
    def registry_provider(self) -> ActionExecutorRegistry:

        actions = []
        for action_class in self._action_classes:
            actions.append(action_class())

        return ActionExecutorRegistry(core_actions=actions)
