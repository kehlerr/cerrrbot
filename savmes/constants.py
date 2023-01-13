from enum import Enum


class MessageActions(str, Enum):
    NONE = "NONE"
    DELETE_REQUEST = "DEL"
    SAVE = "SAVE"
    DOWNLOAD_FILE = "DL"
    DOWNLOAD_ALL = "DLAL"
    DOWNLOAD_DELAY = "DLDE"
    NOTE = "NOTE"
    TODO = "NOTO"
    BOOKMARK = "AB"
    DELETE_FROM_CHAT = "DFC"
    DELETE_NOW = "DELN"
    DELETE_1 = "DEL1"
    DELETE_2 = "DEL2"
    DELETE_3 = "DEL3"
