from enum import StrEnum, auto


class MessageRole(StrEnum):
    USER = auto()
    TOOL = auto()
    AI = auto()
    SYSTEM = auto()
