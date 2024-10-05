import json
import logging
import signal
from uuid import uuid4

import numpy as np
from arroyo.zmq import ZMQListener

from ..schemas import XPSRawEvent, XPSStart, XPSStop

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
    stop_signal = False

    async def start(self):
        logger.info("Listener started")
        while True:
            try:
                if self.stop_signal or received_sigterm["received"]:
                    logger.info("Stopping listener.")
                    break
                json_message = None
                raw_message = await self.zmq_socket.recv()
                try:
                    json_message = json.loads(raw_message.decode("utf-8"))
                except json.JSONDecodeError:
                    pass
                if json_message:
                    json_message = json.loads(raw_message)

                    message_type = json_message["msg_type"]
                    if message_type == "start":
                        await self.operator.process(self._build_start(json_message))
                        continue
                    if message_type == "metadata":
                        await self.operator.process(self._build_stop(json_message))
                        continue
                    if message_type != "image":
                        logger.error(f"Received unexpected message: {json_message}")
                        continue
                else:
                    # Must be an event with an image
                    if logger.getEffectiveLevel() == logging.DEBUG:
                        logger.debug(f"event: {json_message}")
                    # Image should be the next thing received
                    buffer = await self.zmq_socket.recv()
                    await self.operator.process(self._build_event(json_message, buffer))

            except Exception as e:
                logger.error(e)
                if json_message:
                    logger.exception(f"Error dealing with {json_message=}")

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
        return XPSRawEvent(
            frame_number=frame_number, image=array_received, metadata=image_info
        )

    @staticmethod
    def _build_start(message: dict) -> XPSStart:
        message["scan_name"] = f"temporary scan name{uuid4()}"  # temporary

        if logger.getEffectiveLevel() == logging.DEBUG:
            logger.debug(f"start: {message}")
        return XPSStart(scan_name=message["scan_name"], metadata=message)

    @staticmethod
    def _build_stop(message: dict) -> XPSStop:
        if logger.getEffectiveLevel() == logging.DEBUG:
            logger.debug(f"start: {message}")
        metadata = json.loads(message["metadata"])
        return XPSStop(metadata=metadata)
