from datetime import datetime
from typing import Annotated, Any, Self, Sequence, cast

from loguru import logger

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from app.actions import MessageActions
from app.types import ContentType
from .message_action import MessageAction
from .message_document_info import (
    ActionsMenuStored,
    ActionsMenuUpdating,
    PreparedMessageInfo,
    SVM_MsgdocInfo,
)
from .message_media import MediaAttachment, MessageMedia
from .message_source import (
    ChatInfo,
    MessageSourceData,
    MessageSourceInfo,
    UserInfo,
)
from .message_text_info import (
    MessageEntity,
    MessageTextInfo,
)


PyObjectId = Annotated[str, BeforeValidator(str)]


class MessageDocument(BaseModel):
    id: PyObjectId | None = Field(default=None, alias="_id")
    message_id: int = 0
    date: datetime = Field(default_factory=datetime.now)
    edit_date: datetime | None = None

    content_type: ContentType = ContentType.TEXT

    # Encapsulated Domain Components
    source: MessageSourceInfo = Field(default_factory=MessageSourceInfo)
    text_info: MessageTextInfo | None = None
    media: MessageMedia | None = None

    # Additional Telegram / Domain attributes
    author_signature: str | None = None
    via_bot: UserInfo | None = None
    has_protected_content: bool | None = None
    has_media_spoiler: bool | None = None
    link_preview_options: dict[str, Any] | None = None
    reply_to_message: dict[str, Any] | None = None

    # Application Domain Specific Fields
    media_group_id: str | None = None
    is_subsequent_in_media_group: bool = Field(default=False)
    cb_message_info: SVM_MsgdocInfo | None = None
    raw_data: dict[str, Any] | None = None

    model_config = ConfigDict(
        use_enum_values=True,
        extra="allow",
        validate_assignment=True,
        frozen=False,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        defer_build=True,
        protected_namespaces=(),
    )

    def __init__(self, id: str | None = None, **data: Any) -> None:
        if id is not None and "_id" not in data and "id" not in data:
            data["id"] = id
        super().__init__(**data)

    @classmethod
    def from_message(cls, message: Any) -> Self:
        raw_dump = message.model_dump(by_alias=True, exclude_unset=True, exclude_none=True)
        doc = cls.model_validate(raw_dump)
        doc.source = MessageSourceInfo.from_message(message)
        doc.text_info = MessageTextInfo.from_message(message)
        doc.media = MessageMedia.from_message(message)
        if hasattr(message, "content_type"):
            doc.content_type = ContentType.from_val(message.content_type)
        if doc.media and doc.media.rich_message:
            if doc.media.rich_message.extract_media_items():
                doc.content_type = ContentType.RICH_MESSAGE_MEDIA
            else:
                doc.content_type = ContentType.RICH_MESSAGE_TEXT
        doc.raw_data = raw_dump
        return doc

    # --- Source property proxies ---
    @property
    def chat(self) -> ChatInfo:
        return self.source.chat if self.source else ChatInfo()

    # --- Text property proxies ---
    @property
    def text(self) -> str | None:
        return self.text_info.text if self.text_info else None

    @property
    def caption(self) -> str | None:
        return self.text_info.caption if self.text_info else None

    @property
    def entities(self) -> list[MessageEntity] | None:
        return self.text_info.entities if self.text_info else None

    @property
    def caption_entities(self) -> list[MessageEntity] | None:
        return self.text_info.caption_entities if self.text_info else None

    @property
    def message_text(self) -> str | None:
        return self.text_info.message_text if self.text_info else None

    # --- Domain methods ---
    def get_current_action(self) -> MessageAction:
        if not self.cb_message_info:
            raise ValueError("Message info is not set")  # TODO: proper exception

        return self.cb_message_info.action

    def get_current_menu(self) -> ActionsMenuStored:
        if not self.cb_message_info:
            raise ValueError("Message info is not set")  # TODO: proper exception

        return self.cb_message_info.get_current_menu()

    def set_message_info(self, prepared_message_info: PreparedMessageInfo) -> None:
        self.cb_message_info = SVM_MsgdocInfo()

        self.update_message_info(
            new_actions_menu=prepared_message_info.actions_menu,
            new_action=prepared_message_info.action,
            new_ttl=prepared_message_info.ttl,
            entities=prepared_message_info.entities,
        )

    def update_message_info(
        self,
        actions_to_add: ActionsMenuUpdating | None = None,
        actions_to_del: Sequence[MessageAction | str] | None = None,
        new_actions_menu: ActionsMenuUpdating | None = None,
        new_action: MessageAction | None = MessageActions.NONE,
        new_perform_action_at: int | None = None,
        new_ttl: int | None = None,
        entities: list[dict[str, Any]] | None = None,
        reply_action_message_id: int | None = None,
    ) -> None:
        if self.cb_message_info is None:
            return

        self._update_menus(
            actions_to_add=actions_to_add,
            actions_to_del=actions_to_del,
            new_actions_menu=new_actions_menu,
        )

        msg_info = self.cb_message_info
        if new_ttl is not None:
            perform_action_at = int(datetime.now().timestamp()) + new_ttl
            msg_info.perform_action_at = perform_action_at
        elif new_perform_action_at is not None:
            msg_info.perform_action_at = new_perform_action_at

        if new_action is not None:
            msg_info.action = new_action
            if new_action.code == MessageActions.NONE.code:
                msg_info.perform_action_at = 0

        if entities is not None:
            msg_info.entities = entities

        if reply_action_message_id is not None:
            if reply_action_message_id == 0:
                msg_info.reply_action_message_id = None
            else:
                msg_info.reply_action_message_id = reply_action_message_id

    def _update_menus(
        self,
        actions_to_add: ActionsMenuUpdating | None,
        actions_to_del: Sequence[MessageAction | str] | None,
        new_actions_menu: ActionsMenuUpdating | None,
    ) -> None:
        if self.cb_message_info is None:
            return

        msg_info = self.cb_message_info
        actions_menus = msg_info.actions_menus or []
        current_menu = msg_info.actions_menus.pop() if msg_info.actions_menus else {}

        if actions_to_add is not None:
            for action, action_data in actions_to_add.items():
                action_code: str = (
                    action.code if isinstance(action, MessageAction) else action
                )
                current_menu[action_code] = action_data

        if actions_to_del is not None:
            for action_to_del in actions_to_del:
                action_to_del_code: str = (
                    cast(MessageAction, action_to_del).code
                    if isinstance(action_to_del, MessageAction) else action_to_del
                )
                current_menu.pop(action_to_del_code, None)

        if current_menu:
            actions_menus.append(current_menu)

        if new_actions_menu is not None:
            if new_actions_menu:
                actions_menus.append({
                    action.code: action_data
                    for action, action_data in new_actions_menu.items()
                })
            elif actions_menus:
                actions_menus.pop()

        try:
            actions_menus[-2].pop(MessageActions.MENU_BACK.code, None)
        except IndexError:
            ...

        if len(actions_menus) > 1:
            actions_menus[-1][MessageActions.MENU_BACK.code] = {}

        msg_info.actions_menus = actions_menus

    def get_source_data(self) -> MessageSourceData:
        if (
            (forward_origin := self.source.forward_origin) and
            (forward_origin_data := forward_origin.get_message_source_data(self.chat))
        ):
            return forward_origin_data

        from_user = self.source.from_user

        user_id = from_user.id if from_user else None
        title = from_user.full_name if from_user else self.chat.title
        tag = from_user.username if from_user else self.chat.username

        return MessageSourceData(chat_id=self.chat.id, user_id=user_id, title=title, tag=tag)

    def get_message_origin_date(self) -> datetime:
        if forward_origin := self.source.forward_origin:
            return forward_origin.date

        return self.date

    def get_media_attachments(self, content_type: ContentType) -> list[MediaAttachment] | None:
        if not self.media:
            return None

        attachment = self.media.get_content_attachment(content_type)
        if isinstance(attachment, MediaAttachment):
            return [attachment]

        return attachment

    async def delete_reply_message(self, bot: Bot) -> None:
        if not (message_id := self.cb_message_info and self.cb_message_info.reply_action_message_id):
            logger.info("[%s] There is no reply message to delete", self.id)
            return

        try:
            await bot.delete_message(self.chat.id, message_id)
        except TelegramBadRequest as telegram_bad_request:
            logger.warning("No need to delete reply message: %s", telegram_bad_request)