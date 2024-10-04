import dataclasses

import numpy
import pandas


@dataclasses.dataclass
class Result:
    frame_num: dict
    integrated_frame: numpy.ndarray
    detected_peaks: pandas.DataFrame
    vfft: numpy.ndarray
    ifft: numpy.ndarray
    sum: numpy.ndarray


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
