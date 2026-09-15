from enum import StrEnum, auto


class IndexingStatus(StrEnum):
    PENDING = auto()
    ERROR = auto()
    COMPLETED = auto()
