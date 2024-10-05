import numpy as np
from als_arroyo.message import Event, Start, Stop
from pydantic import BaseModel, field_validator


class NumpyArrayModel(BaseModel):
    """
    A Pydantic model for validating numpy.ndarray objects.
    Does not parse array, merely validates that is a np.ndarray
    """

    array: np.ndarray

    @field_validator("array", mode="before")
    def validate_is_numpy_array(cls, v):
        if not isinstance(v, np.ndarray):
            raise TypeError(f"Expected numpy.ndarray, got {type(v)} instead.")
        return v  # Do not modify or parse the array

    class Config:
        arbitrary_types_allowed = True  # Allow numpy.ndarray type


class XPSStart(Start):
    scan_name: str


class XPSRawEvent(Event):
    frame_number: int
    cycle_number: int
    frame: NumpyArrayModel


class XPSStop(Stop):
    # num_frames: int
    pass


class XPSResult(Event):
    frame_number: int
    shape: tuple
    dtype: str
    integrated_frame: NumpyArrayModel
    filtered_integrated_frame: NumpyArrayModel
