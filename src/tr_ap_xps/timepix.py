import logging
from typing import Callable

import msgpack
import numpy as np
import zmq
import zmq.asyncio
from arroyopy.zmq import ZMQListener

from .config import settings
from .schemas import NumpyArrayModel, XPSImageInfo, XPSRawEvent, XPSStart, XPSStop

# from arroyosas.schemas import RawFrameEvent, ImageInfo  # Not used in this file


app_settings = settings.xps_operator

logger = logging.getLogger(__name__)


def setup_zmq():
    ctx = zmq.asyncio.Context()
    lv_zmq_socket = ctx.socket(zmq.SUB)
    lv_zmq_socket.setsockopt(zmq.RCVHWM, 100000)
    logger.info(
        f"binding to: {app_settings.tpx_zmq_listener.zmq_pub_address}:{app_settings.tpx_zmq_listener.zmq_pub_port}"
    )
    lv_zmq_socket.connect(
        f"{app_settings.tpx_zmq_listener.zmq_pub_address}:{app_settings.tpx_zmq_listener.zmq_pub_port}"
    )
    lv_zmq_socket.setsockopt(zmq.SUBSCRIBE, b"")
    return lv_zmq_socket


class XPSTimepixZMQListener(ZMQListener):
    stop_signal = False

    def __init__(self, zmq_socket: zmq.Socket, operator: Callable):
        super().__init__(zmq_socket, operator)

    async def start(self):
        logger.info("Listener started")

        while True:
            try:
                if self.stop_signal:
                    logger.info("Stopping listener.")
                    break

                # Receive first part (metadata)
                metadata_msg_packed = await self.zmq_socket.recv()
                try:
                    metadata = msgpack.unpackb(metadata_msg_packed)
                except Exception as e:
                    logger.error(f"Error unpacking message: {e}")
                    continue

                msg_type = metadata.get("msg_type")

                # Handle different message types
                if msg_type == "start":
                    # Start message - single part only
                    logger.info(
                        f"Received start message: {metadata.get('scan_name', 'unknown')}"
                    )
                    try:
                        # Try to create XPSStart from metadata (may fail if fields don't match)
                        start_msg = self._build_start(metadata)
                        await self.operator.process(start_msg)
                    except Exception as e:
                        logger.warning(
                            f"Could not convert start message to XPSStart: {e}"
                        )
                        logger.info(f"Start message metadata: {metadata}")

                elif msg_type == "stop":
                    # Stop message - single part only
                    logger.info(
                        f"Received stop message: {metadata.get('scan_name', 'unknown')}"
                    )
                    try:
                        # Try to create XPSStop from metadata
                        stop_msg = self._build_stop(metadata)
                        await self.operator.process(stop_msg)
                    except Exception as e:
                        logger.warning(
                            f"Could not convert stop message to XPSStop: {e}"
                        )
                        logger.info(f"Stop message metadata: {metadata}")

                elif msg_type == "event" or msg_type is None:
                    # Event message - try to receive second part (array data)
                    try:
                        # Set short timeout for second part
                        self.zmq_socket.setsockopt(zmq.RCVTIMEO, 1000)
                        raw_message = await self.zmq_socket.recv()
                        # Reset timeout (use default or previous value)
                        self.zmq_socket.setsockopt(zmq.RCVTIMEO, -1)

                        # Must be an event with an image
                        if logger.getEffectiveLevel() == logging.DEBUG:
                            logger.debug(f"event: {metadata.keys()}")

                        await self.operator.process(
                            self._build_event(raw_message, metadata)
                        )
                        logger.debug("event processed")
                    except zmq.Again:
                        logger.warning(
                            "Expected array data but none received, skipping message"
                        )
                        continue
                else:
                    logger.warning(f"Unknown message type: {msg_type}, skipping")

            except Exception as e:
                logger.error(e)

    @staticmethod
    def _build_start(metadata: dict) -> XPSStart:
        """Build XPSStart from metadata dict.

        Note: This is a basic conversion. splash_timepix start messages have different
        fields than XPSStart expects, so this may need adjustment based on your needs.
        """
        # Create Rectangle using a dict with alias keys
        detector_x = metadata.get("detector_size_x", 256)
        detector_y = metadata.get("detector_size_y", 256)
        rectangle_dict = {
            "Left": 0,
            "Top": 0,
            "Right": detector_x,
            "Bottom": detector_y,
            "Rotation": 0,
        }

        # Create XPSStart using a dict with alias keys (as Pydantic expects)
        # This matches the LabVIEW JSON format
        start_dict = {
            "msg_type": "start",
            "scan_name": metadata.get("scan_name", "unknown"),
            "Binding Energy": 0.0,  # Not applicable for TimePix
            "F_Trigger": 0,
            "F_Un-Trigger": 0,
            "F_Dead": 0,
            "F_Reset": 0,
            "CCD_nx": metadata.get("detector_size_x", 256),
            "CCD_ny": metadata.get("detector_size_y", 256),
            "Pass Energy": 0.0,
            "Center Energy": 0.0,
            "Offset Energy": 0.0,
            "Lens Mode": "TimePix3",
            "Rectangle": rectangle_dict,  # Pass dict, not object
            "dt": metadata.get("t_delta_ns", 10.0) / 1e9,  # Convert ns to seconds
            "Photon Energy": 0.0,
            "File Ver": "1.0.0",
            "data_type": "uint32",
        }
        return XPSStart(**start_dict)

    @staticmethod
    def _build_stop(metadata: dict) -> XPSStop:
        """Build XPSStop from metadata dict."""
        # XPSStop doesn't have required fields, so we can create an empty one
        return XPSStop()

    @staticmethod
    def _build_event(
        image: bytes,
        metadata: dict,
    ) -> XPSRawEvent:
        shape = tuple(metadata["shape"])
        dtype = metadata["dtype"]

        image_info = XPSImageInfo(
            frame_number=0, width=shape[0], height=shape[1], data_type=dtype
        )

        array_received = np.frombuffer(image, dtype=dtype).reshape(shape)
        image_info.frame_number = metadata.get("flush_number", 0)
        return XPSRawEvent(
            image=NumpyArrayModel(array=array_received), image_info=image_info
        )


if __name__ == "__main__":
    from .log_utils import setup_logger  # noqa: F401

    class DummyOperator:
        async def process(self, message):
            """Process different message types."""
            if isinstance(message, XPSStart):
                logger.info(
                    f"Dummy operator received START: scan_name={message.scan_name}"
                )
            elif isinstance(message, XPSStop):
                logger.info("Dummy operator received STOP")
            elif isinstance(message, XPSRawEvent):
                logger.info(
                    f"Dummy operator received EVENT with image shape: {message.image.array.shape}"
                )
            else:
                logger.warning(
                    f"Dummy operator received unknown message type: {type(message)}"
                )

    setup_logger(logger)
    zmq_socket = setup_zmq()
    listener = XPSTimepixZMQListener(zmq_socket=zmq_socket, operator=DummyOperator())
    import asyncio

    asyncio.run(listener.start())
