from typing import Literal

from pydantic import BaseModel, Field

from arroyo.schemas import DataFrameModel, Event, Message, NumpyArrayModel, Start, Stop

"""
    This module defines schemas for XPS (X-ray Photoelectron Spectroscopy) messages and events using
    Pydantic models. It includes classes for different types of messages and events such as
    start, stop, raw events, and results. These classes serve as data transfer classes within the
    tr_ap_xps pipeline.

    Pydantic is used for several reasons.
    - It provides validated of messages
    - Using pydantic's alias mechanism, it provides a mapping between the json field names produced by LabVIEW and
        python field name.
    - Pydantic provides easy translation between json and python structures

    Three of these models define the incoming message from LabView, one defines the outgoing message
    from our Operators.

"""


class Rectangle(BaseModel):
    left: int = Field(..., alias="Left")
    top: int = Field(..., alias="Top")
    right: int = Field(..., alias="Right")
    bottom: int = Field(..., alias="Bottom")
    rotation: int = Field(..., alias="Rotation")


class XPSMessage(Message):
    pass


class XPSStart(Start, XPSMessage):
    msg_type: str = Literal["start"]
    binding_energy: float = Field(..., alias="Binding Energy")
    msg_type: str = Field("start", alias="msg_type")
    """
    LabVIEW Message:

    Incoming message from LabView at the start of a scan.
    Expects incoming message to be JSON.
    An example with nonsense values:

    {
        "msg_type": "start",
        "F_Trigger": 13,
        "F_Un-Trigger": 38,
        "F_Dead": 45,
        "F_Reset": 46,
        "CCD_nx": 1392,
        "CCD_ny": 1040,
        "Pass Energy": 200,
        "Center Energy": 3308,
        "Offset Energy": -0.837,
        "Lens Mode": "X6-26Mar2022-test",
        "Rectangle": {
            "Left": 148,
            "Top": 385,
            "Right": 1279,
            "Bottom": 654,
            "Rotation": 0
        },
        "data_type": "U8",
        "dt": 0.0820741786426572,
        "Photon Energy": 3999.99740398402,
        "Binding Energy": 90,
        "File Ver": "1.0.0"
    }


    """

    binding_energy: float = Field(..., alias="Binding Energy")
    scan_name: str = Field(..., alias="scan_name")
    f_trigger: int = Field(..., alias="F_Trigger")
    f_untrigger: int = Field(..., alias="F_Un-Trigger")
    f_dead: int = Field(..., alias="F_Dead")
    f_reset: int = Field(..., alias="F_Reset")
    ccd_nx: int = Field(..., alias="CCD_nx")
    ccd_ny: int = Field(..., alias="CCD_ny")
    pass_energy: float = Field(..., alias="Pass Energy")
    center_energy: float = Field(..., alias="Center Energy")
    offset_energy: float = Field(..., alias="Offset Energy")
    lens_mode: str = Field(..., alias="Lens Mode")
    rectangle: Rectangle = Field(..., alias="Rectangle")
    dt: float = Field(..., alias="dt")
    photon_energy: float = Field(..., alias="Photon Energy")
    binding_energy: float = Field(..., alias="Binding Energy")
    file_ver: str = Field(..., alias="File Ver")
    data_type: str = Field(..., alias="data_type")


class XPSImageInfo(BaseModel):
    frame_number: int
    width: int
    height: int
    data_type: str


class XPSRawEvent(Event, XPSMessage):
    """

    LabVIEW Message:
    {
        "msg_type": "event",
        "Frame Number": 1
    }
    """

    msg_type: str = Literal["event"]
    image: NumpyArrayModel
    image_info: XPSImageInfo


class XPSStop(Stop, XPSMessage):
    """
    {
        "msg_type": "stop",
        "Num Frames": 1
    }

    """

    pass
    # num_frames: int = Field(..., alias="Num Frames")


class XPSResult(Event, XPSMessage):
    """
    This model is output from Operators and used by Publishers after
    calculations are made.
    """

    frame_number: int
    integrated_frames: NumpyArrayModel
    detected_peaks: DataFrameModel
    vfft: NumpyArrayModel
    ifft: NumpyArrayModel
    shot_num: int
    shot_sum: NumpyArrayModel
    shot_mean: NumpyArrayModel
    shot_std: NumpyArrayModel


class XPSResultStop(Stop, XPSMessage):
    msg_type: str = Literal["result_stop"]
    function_timings: DataFrameModel
