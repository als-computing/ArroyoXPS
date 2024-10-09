from arroyo.schemas import DataFrameModel, Event, Message, NumpyArrayModel, Start, Stop
from pydantic import BaseModel, Field

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
    """
    This model is used in the XPSStart message.
    Documnetation of the incoming JSON is found there.
    """

    left: int = Field(..., alias="Left")
    top: int = Field(..., alias="Top")
    right: int = Field(..., alias="Right")
    bottom: int = Field(..., alias="Bottom")
    rotation: int = Field(..., alias="Rotation")


class XPSMessage(Message):
    pass


class XPSStart(Start, XPSMessage):
    """
    LabVIEW Message:

    Incoming message from LabView at the start of a scan.
    Expects incoming message to be JSON.
    An example with nonsense values:

    {
        "XPSStart": {
            "Binding Energy (eV)": 42.0001,
            "frame_per_cycle": 10,
            "scan_name": "Don't panic!",
            "F_trigger": 42,
            "F_Un-Trigger": 42,
            "F_Dead": 42,
            "F_Reset": 42,
            "CCD_nx": 42,
            "CCD_ny": 42,
            "Pass Energy": 42.0001,
            "Center Energy": 42.001,
            "Offset Energy": 42.001,
            "Lens Mode: "Magrathea",
            "Rectangle": {
                "Left": 42,
                "Top": 42,
                "Right": 42,
                "Bottom": 42
            },
            "Notes": "So long and thanks for all the fish",
            "dt": 42.00001,
            "Photon Energy": 42.0001,
            "Binding Energy": 42.0001,
            "File Ver": "Earth V2"
            "Stream": "Heart of Gold"
        }
    }

    """

    binding_energy: float = Field(..., alias="Binding Energy (eV)")
    frames_per_cycle: int = Field(..., alias="frame_per_cycle")
    scan_name: str = Field(..., alias="scan_name")
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


class XPSImageInfo(BaseModel):
    """
    LabVIEW Message:

        Incoming mesesage with every frame.
        For each frame, LabVIEW sends a json document with frame information.
        Expects incoming message to be JSON.
        An example with nonsense values:

        {
            "XPSImageInfo": {
                "Frame Number": 42,
                "Width": 1042,
                "Height": 1042,
                "Data Type": "U8"
            }
        }
    """

    frame_number: int = Field(..., alias="Frame Number")
    width: int = Field(..., alias="Width")
    height: int = Field(..., alias="Height")
    data_type: str = Field(..., alias="data_type")


class XPSRawEvent(Event, XPSMessage):
    """
    LabVIEW Message:
        This model is passed to operators from listeners. Documentation of the
        image_info json is found in that model.

        Data Events come from LabView in two parts. One part is a
        json document with frame information, the other contains the
        raw frame bytes.
    """

    image: NumpyArrayModel
    image_info: XPSImageInfo


class XPSStop(Stop, XPSMessage):
    """
    LabVIEW Message:

     {
        "XPSStop": {
            "Num Frames": 42
        }
    }
    """

    num_frames: int = Field(..., alias="Num Frames")


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
    sum: NumpyArrayModel
