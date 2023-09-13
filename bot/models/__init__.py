from .collection.base import CollectionModel as MessagesBaseCollection
from .collection.messages import NewMessagesCollection, SavedMessagesCollection
from .message_action import MessageAction, CustomMessageAction

collections = [NewMessagesCollection, SavedMessagesCollection]


__all__ = (
    "MessageAction",
    "CustomMessageAction",
    "NewMessagesCollection",
    "SavedMessagesCollection",
    "MessagesBaseCollection",
    "collections"
)