from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


@dataclass
class Polygon:
    points: List[Tuple[float]]
    fill_color: str
    line_color: str
    line_width: float


class IFDType(str, Enum):
    tile = 'tile'
    thumbnail = 'thumbnail'
    label = 'label'
    macro = 'macro'
    other = 'other'
