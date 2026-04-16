import logging
from typing import Callable

import msgpack
import numpy as np
import zmq
import zmq.asyncio
from arroyopy.zmq import ZMQListener

from .schemas import NumpyArrayModel, XPSImageInfo, XPSRawEvent, XPSStart, XPSStop

from arroyopy.operator import Operator



logger = logging.getLogger(__name__)


# CHANGED: removed app_settings; accepts address/port as parameters instead
def setup_zmq(
    zmq_pub_address: str = "tcp://localhost",
    zmq_pub_port: int = 5657,
):
    ctx = zmq.asyncio.Context()
    lv_zmq_socket = ctx.socket(zmq.SUB)
    lv_zmq_socket.setsockopt(zmq.RCVHWM, 100000)
    logger.info(f"binding to: {zmq_pub_address}:{zmq_pub_port}")
    lv_zmq_socket.connect(f"{zmq_pub_address}:{zmq_pub_port}")
    lv_zmq_socket.setsockopt(zmq.SUBSCRIBE, b"")
    return lv_zmq_socket

class XPSTimepixZMQListener(ZMQListener):
    stop_signal = False

    def __init__(self, zmq_socket: zmq.Socket, operator: Operator):
        super().__init__(operator, zmq_socket)

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
        """Build XPSStart from Timepix metadata.

        CHANGED: XPSStart fields are all Optional now, so pass metadata directly.
        No need to fabricate fake LabVIEW fields (Rectangle, F_Reset, etc.).
        """
        return XPSStart(**metadata)

    @staticmethod
    def _build_stop(metadata: dict) -> XPSStop:
        """Build XPSStop from Timepix metadata.

        CHANGED: XPSStop accepts extra fields now, so pass metadata directly.
        """
        return XPSStop(**metadata)

    @staticmethod
    def _build_event(
        image: bytes,
        metadata: dict,
    ) -> XPSRawEvent:
        shape = tuple(metadata["shape"])
        dtype = metadata["dtype"]

        image_info = XPSImageInfo(
            frame_number=metadata.get("flush_number", 0),
            width=shape[0],
            height=shape[1],
            data_type=dtype,
            timestamp=metadata.get("timestamp"),
            cycles_in_flush=metadata.get("cycles_in_flush"),
            total_cycles=metadata.get("total_cycles"),
        )

        array_received = np.frombuffer(image, dtype=dtype).reshape(shape)
        
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

# ADDED: factory function for YAML instantiation
def xps_timepix_listener_factory(
    operator,
    zmq_pub_address: str = "tcp://localhost",
    zmq_pub_port: int = 5657,
) -> XPSTimepixZMQListener:
    socket = setup_zmq(zmq_pub_address, zmq_pub_port)
    return XPSTimepixZMQListener(operator=operator, zmq_socket=socket)