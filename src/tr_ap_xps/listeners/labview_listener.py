import json
import logging
from uuid import uuid4

import numpy as np
from arroyo.zmq import ZMQListener
import zmq.asyncio

from ..config import settings
from ..schemas import (
    NumpyArrayModel,
    XPSImageInfo,
    XPSRawEvent,
    XPSStart,
    XPSStop
)

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

app_settings = settings.xps

logger = logging.getLogger(__name__)

def setup_zmq():
    ctx = zmq.asyncio.Context()
    lv_zmq_socket = ctx.socket(zmq.SUB)
    logger.info(
        f"binding to: {app_settings.lv_zmq_listener.zmq_pub_address}:{app_settings.lv_zmq_listener.zmq_pub_port}"
    )
    lv_zmq_socket.connect(
        f"{app_settings.lv_zmq_listener.zmq_pub_address}:{app_settings.lv_zmq_listener.zmq_pub_port}"
    )
    lv_zmq_socket.setsockopt(zmq.SUBSCRIBE, b"")
    return lv_zmq_socket


class XPSLabviewZMQListener(ZMQListener):
    stop_signal = False

    async def start(self):
        logger.info("Listener started")
        while True:
            json_message = None
            try:
                if self.stop_signal:
                    logger.info("Stopping listener.")
                    break
                raw_message = await self.zmq_socket.recv()
                # print(raw_message[0:300])
                try:
                    json_message = json.loads(raw_message.decode("utf-8"))
                except json.JSONDecodeError:
                    pass
                if json_message:
                    message_type = json_message.get("msg_type")
                    if message_type == "start":
                        logger.info(f"Start message processed: {json_message['scan_name']}")
                        await self.operator.process(self._build_start(json_message))
                        continue
                
                    elif message_type == "stop":
                        logger.info("Stop message received")
                        await self.operator.process(self._build_stop(json_message))
                        continue
                    elif message_type == "event":
                        buffer = await self.zmq_socket.recv()
                        # Must be an event with an image
                        if logger.getEffectiveLevel() == logging.DEBUG:
                            logger.debug(f"event: {json_message}")
                        # Image should be the next thing received
                        if not json_message or not buffer:
                            logger.error("Received unexpected message")
                            continue
                        await self.operator.process(self._build_event(json_message, buffer))
            except Exception as e:
                logger.error(e)
                if json_message:
                    logger.exception(f"Error dealing with  message")

    @staticmethod
    def _build_event(message: dict, buffer: bytes) -> XPSRawEvent:
        image_info = XPSImageInfo(**message)
        shape = (image_info.width, image_info.height)
        dtype = DATATYPE_MAP.get(image_info.data_type)
        if not dtype:
            logger.error(f"Received unexpected data type: {image_info}")
        array_received = np.frombuffer(buffer, dtype=dtype).reshape(shape)
        return XPSRawEvent(
                    image=NumpyArrayModel(array=array_received),
                    image_info=image_info
        )

    @staticmethod
    def _build_start(message: dict) -> XPSStart:
        message["scan_name"] = f"temporary scan name{uuid4()}"  # temporary

        if logger.getEffectiveLevel() == logging.DEBUG:
            logger.debug(f"start: {message}")
        return XPSStart(**message)

    @staticmethod
    def _build_stop(message: dict) -> XPSStop:
        if logger.getEffectiveLevel() == logging.DEBUG:
            logger.debug(f"stop: {message}")
        return XPSStop(**message)
