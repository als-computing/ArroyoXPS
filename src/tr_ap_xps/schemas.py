import numpy
import pandas
from typing import Literal

from arroyo.schemas import Event, Message, Start, Stop
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
    msg_type: str = Literal["start"]
    binding_energy: float = Field(..., alias="Binding Energy (eV)")
    frames_per_cycle: int = Field(..., alias="frames_per_cycle")
    msg_type: str = Field("start", alias="msg_type")
    scan_name: str = Field(..., alias="scan_name")
    


class XPSImageInfo(BaseModel):
    frame_number: int = Field(..., alias="Frame Number")
    width: int = Field(..., alias="Width")
    height: int = Field(..., alias="Height")
    data_type: str = Field(..., alias="Type")


class XPSRawEvent(Event, XPSMessage):
    msg_type: str = Literal["event"]
    image: NumpyArrayModel
    image_info: XPSImageInfo
    


class Rectangle(BaseModel):
    left: int = Field(..., alias="F_Trigger")
    top: int = Field(..., alias="F_Trigger")
    right: int = Field(..., alias="F_Trigger")
    bottom: int = Field(..., alias="F_Trigger")
    rotation: int = Field(..., alias="F_Trigger")


class XPSStop(Stop, XPSMessage):
    msg_type: str = Literal["sttop"]
    f_trigger: int = Field(..., alias="F_Trigger")
    f_untrigger: int = Field(..., alias="F_Un-Trigger")
    f_dead: int = Field(..., alias="F_Dead")
    f_reset: int = Field(..., alias="F_Reset")
    ccd_nx: int = Field(..., alias="CCD_nx")
    ccd_ny: int = Field(..., alias="CCD_ny")
    pass_energy: int = Field(..., alias="Pass Energy")
    center_energy: int = Field(..., alias="Center Energy")
    offset_energy: int = Field(..., alias="Offset Energy")
    lens_mode: str = Field(..., alias="Lens Mode")
    rectangle: Rectangle = Field(..., alias="Rectangle")
    notes: str = Field(..., alias="Notes")
    dt: float = Field(..., alias="dt")
    photon_energy: float = Field(..., alias="Photon Engergy")
    binding_energy: float = Field(..., alias="Binding Energy")
    file_ver: str = Field(..., alias="File Ver")
    stream: str = Field(..., alias="Strean")



class XPSResult(Event, XPSMessage):
    frame_number: int
    integrated_frames: NumpyArrayModel
    detected_peaks: DataFrameModel
    vfft: NumpyArrayModel
    ifft: NumpyArrayModel
    sum: NumpyArrayModel

class XPSResultStop(Stop, XPSMessage):
    msg_type: str = Literal["result_stop"]
    function_timings: DataFrameModel