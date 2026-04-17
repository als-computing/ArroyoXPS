from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from arroyopy.schemas import DataFrameModel, Event, Message, NumpyArrayModel, Start, Stop

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
    """
    Incoming start message from ZMQ. Supports both LabVIEW and Timepix sources.

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

    Timepix Message (msgpack-encoded, from splash_timepix server):

    {
        "msg_type": "start",
        "scan_name": "acquisition_20250128T143022Z_a1b2c3d4",
        "tdc_frequency_hz": 1000.0,
        "t_delta_ns": 10.0,
        "t_cycle_ns": 1000000.0,
        "n_bins": 100,
        "detector_size_x": 256,
        "detector_size_y": 256,
        "flush_interval_s": 1.0,
        "cycles_per_flush": 1000,
        "tdc_channel": 1,
        "tdc_edge": "rising",
        "collapse_y": false,
        "zmq_port": 5657,
        "tcp_port": 9090
    }

    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    msg_type: str = Field("start", alias="msg_type")

    # LabVIEW fields — all Optional so Timepix start messages are also accepted
    binding_energy: Optional[float] = Field(None, alias="Binding Energy")
    scan_name: Optional[str] = Field(None, alias="scan_name")
    f_trigger: Optional[int] = Field(None, alias="F_Trigger")
    f_untrigger: Optional[int] = Field(None, alias="F_Un-Trigger")
    f_dead: Optional[int] = Field(None, alias="F_Dead")
    f_reset: Optional[int] = Field(None, alias="F_Reset")
    ccd_nx: Optional[int] = Field(None, alias="CCD_nx")
    ccd_ny: Optional[int] = Field(None, alias="CCD_ny")
    pass_energy: Optional[float] = Field(None, alias="Pass Energy")
    center_energy: Optional[float] = Field(None, alias="Center Energy")
    offset_energy: Optional[float] = Field(None, alias="Offset Energy")
    lens_mode: Optional[str] = Field(None, alias="Lens Mode")
    rectangle: Optional[Rectangle] = Field(None, alias="Rectangle")
    dt: Optional[float] = Field(None, alias="dt")
    photon_energy: Optional[float] = Field(None, alias="Photon Energy")
    file_ver: Optional[str] = Field(None, alias="File Ver")
    data_type: Optional[str] = Field(None, alias="data_type")

    # Timepix fields from splash_timepix start message
    tdc_frequency_hz: Optional[float] = None
    t_delta_ns: Optional[float] = None
    t_cycle_ns: Optional[float] = None
    n_bins: Optional[int] = None
    detector_size_x: Optional[int] = None
    detector_size_y: Optional[int] = None
    flush_interval_s: Optional[float] = None
    cycles_per_flush: Optional[int] = None
    tdc_channel: Optional[int] = None
    tdc_edge: Optional[str] = None
    collapse_y: Optional[bool] = None
    zmq_port: Optional[int] = None
    tcp_port: Optional[int] = None


class XPSImageInfo(BaseModel):
    frame_number: int
    width: int
    height: int
    data_type: str
    # Timepix event metadata
    timestamp: Optional[float] = None
    cycles_in_flush: Optional[int] = None
    total_cycles: Optional[int] = None


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
    LabVIEW Message:
    {
        "msg_type": "stop",
        "Num Frames": 1
    }

    Timepix Message:
    {
        "msg_type": "stop",
        "scan_name": "acquisition_20250128T143022Z_a1b2c3d4",
        "total_flushes": 9,
        "total_cycles": 99,
        "total_packets": 50000,
        "acquisition_duration_s": 28.91
    }
    """

    model_config = ConfigDict(extra="allow")

    scan_name: Optional[str] = None
    total_flushes: Optional[int] = None
    total_cycles: Optional[int] = None
    total_packets: Optional[int] = None
    acquisition_duration_s: Optional[float] = None


# ADDED: operator output types — clean separation from ZMQ input types

class XPSResultStart(Start, XPSMessage):
    """
    Published by XPSOperator when a new scan begins.
    Downstream publishers use this to signal that a new acquisition has started.
    """
    msg_type: str = Literal["result_start"]
    scan_name: Optional[str] = None


class XPSResult(Event, XPSMessage):
    """
    This model is output from Operators and used by Publishers after
    calculations are made.
    """

    frame_number: Optional[int] = None
    integrated_frames: NumpyArrayModel
    detected_peaks: Optional[DataFrameModel] = None
    vfft: Optional[NumpyArrayModel] = None
    ifft: Optional[NumpyArrayModel] = None
    shot_num: Optional[int] = None
    shot_recent: Optional[NumpyArrayModel] = None
    shot_mean: Optional[NumpyArrayModel] = None
    shot_std: Optional[NumpyArrayModel] = None


class XPSResultStop(Stop, XPSMessage):
    """
    Published by XPSOperator when processing ends.
    """
    msg_type: str = Literal["result_stop"]
    function_timings: Optional[DataFrameModel] = None
