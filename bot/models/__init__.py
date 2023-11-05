from .collection.base import CollectionModel as MessagesBaseCollection
from .collection.messages import NewMessagesCollection, SavedMessagesCollection
from .message_action import MESSAGE_ACTION_NONE, CustomMessageAction, MessageAction
from .message_button import MessageButton
from .message_document import COMMON_GROUP_KEY, MessageDocument
from .message_document_info import SVM_MsgdocInfo, SVM_ReplyInfo
from .plugin_model import PluginModel

collections = [NewMessagesCollection, SavedMessagesCollection]


__all__ = (
    "collections",
    "COMMON_GROUP_KEY",
    "CustomMessageAction",
    "MessageAction",
    "NewMessagesCollection",
    "MessagesBaseCollection",
    "MessageButton",
    "MessageDocument",
    "MESSAGE_ACTION_NONE",
    "PluginModel",
    "SavedMessagesCollection",
    "SVM_MsgdocInfo",
    "SVM_ReplyInfo",
)