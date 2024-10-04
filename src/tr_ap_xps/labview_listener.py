import logging
import signal
from uuid import uuid4

import numpy as np
from arroyo.zmq import ZMQListener

from .schemas import XPSRawEvent, XPSStart, XPSStop

# Maintain a map of LabView datatypes. LabView sends BigE,
# and Numpy assumes LittleE, so adjust that too.
# LabView also has an 'Extended Float' and I don't know how to map that.
DATATYPE_MAP = {
    "U8": np.dtype(np.uint8).newbyteorder(">"),
    "U16": np.dtype(np.uint16).newbyteorder(">"),
    "U32": np.dtype(np.uint32).newbyteorder(">"),
    "U64": np.dtype(np.uint64).newbyteorder(">"),
    "I8": np.dtype(np.int8).newbyteorder(">"),
    "I16": np.dtype(np.int16).newbyteorder(">"),
    "I32": np.dtype(np.int32).newbyteorder(">"),
    "I64": np.dtype(np.int64).newbyteorder(">"),
    "Single Float": np.dtype(np.single).newbyteorder(">"),
    "Double Float": np.dtype(np.double).newbyteorder(">"),
}

logger = logging.getLogger(__name__)

received_sigterm = {"received": False}  # Define the variable received_sigterm


def handle_sigterm(signum, frame):
    logger.info("SIGTERM received, stopping...")
    received_sigterm["received"] = True


# Register the handler for SIGTERM
signal.signal(signal.SIGTERM, handle_sigterm)


class XPSLabviewZMQListener(ZMQListener):
    async def start(self):
        logger.info("Listener started")
        while True:
            try:
                message = self.zmq_socket.recv()

                if self.stop or received_sigterm["received"]:
                    logger.info("Stopping listener.")
                    break

                message = self.zmq_socket.recv_json()
                logger.info(f"{message=}")
                message_type = message["msg_type"]
                if message_type == "start":
                    return self._build_start(message)
                if message_type == "metadata":
                    return self._build_stop(message)

                if message_type != "image":
                    logger.error(f"Received unexpected message: {message}")
                    continue

                # Must be an event with an image
                image_info = message
                if logger.getEffectiveLevel() == logging.DEBUG:
                    logger.debug(f"event: {image_info}")
                # Image should be the next thing received
                buffer = self.zmq_socket.recv()
                return self._build_event(image_info, buffer)

            except Exception as e:
                logger.error(e)
                if message:
                    logger.exception(f"Error dealing with {message=}")

    @staticmethod
    def _build_event(image_info: dict, buffer: bytes) -> XPSRawEvent:
        shape = (image_info["Width"], image_info["Height"])
        frame_number = image_info["Frame Number"]
        dtype = DATATYPE_MAP.get(image_info["data_type"])
        if not dtype:
            logger.error(f"Received unexpected data type: {image_info}")
        array_received = np.frombuffer(buffer, dtype=dtype).reshape(shape)
        if logger.getEffectiveLevel() == logging.DEBUG:
            logger.debug(
                f"received: {frame_number=} {shape=} {dtype=} {array_received}"
            )
        return XPSRawEvent(frame_number=frame_number, image=array_received)

    @staticmethod
    def _build_start(self, message: dict) -> XPSStart:
        message["scan_name"] = f"temporary scan name{uuid4()}"  # temporary

        if logger.getEffectiveLevel() == logging.DEBUG:
            logger.debug(f"start: {message}")
        return XPSStart(scan_name=message["scan_name"])

    @staticmethod
    def _build_stop(
        self,
        message: dict,
    ) -> XPSStop:
        if logger.getEffectiveLevel() == logging.DEBUG:
            logger.debug(f"start: {message}")
        return XPSStop(num_frames=message["num_frames"])
