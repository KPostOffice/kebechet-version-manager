from enum import Enum

class ReleaseType(Enum):
    patch = 0
    minor = 1
    major = 2
    pre = 3
    build = 4
    finalize = 5
    calendar = 6