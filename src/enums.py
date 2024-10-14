from enum import Enum


class Operation(Enum):
    AVG = 1
    MEDIAN = 2
    FIXED = 3


class DataInterval(Enum):
    OFF = 'Off'
