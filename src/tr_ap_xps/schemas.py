import numpy
import pandas
from als_arroyo.message import Event, Message, Start, Stop
from pydantic import BaseModel, Field, field_validator


class DataFrameModel(BaseModel):
    """
    A Pydantic model for validating pd.DataFrame objects.
    Does not parse array, merely validates that is a pd.DataFrame
    """

    df: pandas.DataFrame

    @field_validator("df", mode="before")
    def validate_is_numpy_array(cls, v):
        if not isinstance(v, pandas.DataFrame):
            raise TypeError(f"Expected pd.DataFrame, got {type(v)} instead.")
        return v  # Do not modify or parse the array

    class Config:
        arbitrary_types_allowed = True  # Allow numpy.ndarray type


class NumpyArrayModel(BaseModel):
    """
    A Pydantic model for validating numpy.ndarray objects.
    Does not parse array, merely validates that is a np.ndarray
    """

    array: numpy.ndarray

    @field_validator("array", mode="before")
    def validate_is_numpy_array(cls, v):
        if not isinstance(v, numpy.ndarray):
            raise TypeError(f"Expected numpy.ndarray, got {type(v)} instead.")
        return v  # Do not modify or parse the array

    class Config:
        arbitrary_types_allowed = True  # Allow numpy.ndarray type


class XPSMessage(Message):
    pass


class XPSStart(Start, XPSMessage):
    binding_energy: float = Field(..., alias="Binding Energy (eV)")
    frames_per_cycle: int = Field(..., alias="frame_per_cycle")
    msg_type: str = Field(..., alias="msg_type")
    scan_name: str = Field(..., alias="scan_name")


class XPSImageInfo(BaseModel):
    frame_number: int = Field(..., alias="Frame Number")
    width: int = Field(..., alias="Width")
    height: int = Field(..., alias="Height")
    data_type: str = Field(..., alias="data_type")


class XPSRawEvent(Event, XPSMessage):
    image: NumpyArrayModel
    image_info: XPSImageInfo


class XPSStop(Stop, XPSMessage):
    # num_frames: int
    pass


class XPSResult(Event, XPSMessage):
    frame_number: int
    integrated_frames: NumpyArrayModel
    detected_peaks: DataFrameModel
    vfft: NumpyArrayModel
    ifft: NumpyArrayModel
    sum: NumpyArrayModel
