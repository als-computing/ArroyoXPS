import dataclasses

import numpy


@dataclasses.dataclass
class Start:
    metadata: dict


@dataclasses.dataclass
class Event:
    frame_num: int
    image_info: dict
    image: numpy.ndarray


@dataclasses.dataclass
class Stop:
    metadata: dict
