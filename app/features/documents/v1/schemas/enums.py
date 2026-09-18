from enum import StrEnum, auto


class IndexingStatus(StrEnum):
    PROCESSING = auto()
    FAILED = auto()
    COMPLETED = auto()
