from .collection.base import CollectionModel as MessagesBaseCollection
from .collection.messages import NewMessagesCollection, SavedMessagesCollection


collections = [NewMessagesCollection, SavedMessagesCollection]


__all__ = ("NewMessagesCollection", "SavedMessagesCollection", "MessagesBaseCollection", "collections")