import json
import logging
import queue
import signal
from typing import Callable
from uuid import uuid4

import numpy as np
import zmq

from .beamline_events import Event, Start, Stop

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


class LabviewListener:
    def __init__(
        self,
        raw_message_queue: queue.Queue,
        zmq_pub_address: str = "tcp://127.0.0.1",
        zmq_pub_port: int = 5555,
    ):
        self.zmq_pub_address = zmq_pub_address
        self.zmq_pub_port = zmq_pub_port
        self.raw_message_queue = raw_message_queue
        self.stop = False

    def start(self):
        ctx = zmq.Context()
        socket = ctx.socket(zmq.SUB)
        logger.info(f"binding to: {self.zmq_pub_address}:{self.zmq_pub_port}")
        socket.connect(f"{self.zmq_pub_address}:{self.zmq_pub_port}")
        socket.setsockopt(zmq.SUBSCRIBE, b"")

        image_info = {}
        frame_num = 0
        while True:
            try:
                if self.stop or received_sigterm["received"]:
                    logger.info("Stopping listener.")
                    break
                message = socket.recv()
                try:
                    message_json = json.loads(message)
                except:
                    image = message
                    message_json = None

                if message_json:
                    # logger.info(f"{message=}")
                    message_type = message_json["msg_type"]
                    if message_type == "start":
                        message_json[
                            "scan_name"
                        ] = f"temporary scan name{uuid4()}"  # temporary
                        self.raw_message_queue.put(Start(message_json))

                        logger.info(f"start: {message}")
                        continue
                    if message_type == "metadata":
                        self.raw_message_queue.put(Stop(message_json))
                        image_info = {}
                        frame_num = 0
                        continue
                    if message_type == "image":
                        image_info = {
                            "shape": (message_json["Width"], message_json["Height"]),
                            "dtype": DATATYPE_MAP.get(message_json["data_type"]),
                        }
                        continue
                else:  # must be an image
                    if "dtype" not in image_info:
                        logger.error("Out of order messages.")
                        continue
                    array_received = np.frombuffer(
                        image, dtype=image_info["dtype"]
                    ).reshape(image_info["shape"])
                    if self.raw_message_queue.qsize() > 100:
                        self.raw_message_queue.get()  # Remove oldest item from the queue
                    self.raw_message_queue.put(
                        Event(frame_num, image_info, array_received)
                    )
                    frame_num += 1

            except Exception as e:
                logger.error(e)

    def stop(self):
        self.stop = True


class LabviewListener2:
    def __init__(
        self,
        raw_message_queue: queue.Queue,
        zmq_pub_address: str = "tcp://127.0.0.1",
        zmq_pub_port: int = 5555,
    ):
        self.zmq_pub_address = zmq_pub_address
        self.zmq_pub_port = zmq_pub_port
        self.raw_message_queue = raw_message_queue
        self.stop = False

    def start(self):
        ctx = zmq.Context()
        socket = ctx.socket(zmq.SUB)
        logger.info(f"binding to: {self.zmq_pub_address}:{self.zmq_pub_port}")
        socket.connect(f"{self.zmq_pub_address}:{self.zmq_pub_port}")
        socket.setsockopt(zmq.SUBSCRIBE, b"")

        while True:
            try:
                if self.stop or received_sigterm["received"]:
                    logger.info("Stopping listener.")
                    break
                message = socket.recv_json()
                # logger.info(f"{message=}")
                message_type = message["msg_type"]
                if message_type == "start":
                    message["scan_name"] = f"temporary scan name{uuid4()}"  # temporary
                    self.raw_message_queue.put(Start(message))
                    if logger.getEffectiveLevel() == logging.DEBUG:
                        logger.debug(f"start: {message}")
                    continue
                if message_type == "metadata":
                    self.raw_message_queue.put(Stop(message))
                    continue
                if message_type != "image":
                    logger.error(f"Received unexpected message: {message}")
                    continue
                # Must be an event with an image
                image_info = message
                if logger.getEffectiveLevel() == logging.DEBUG:
                    logger.debug(f"event: {image_info}")

                # Image should be the next thing received
                buffer = socket.recv()
                shape = (image_info["Width"], image_info["Height"])
                frame_number = image_info["Frame Number"]
                dtype = DATATYPE_MAP.get(image_info["data_type"])
                if not dtype:
                    logger.error(f"Received unexpected data type: {image_info}")
                    continue
                array_received = np.frombuffer(buffer, dtype=dtype).reshape(shape)
                if logger.getEffectiveLevel() == logging.DEBUG:
                    logger.debug(
                        f"received: {frame_number=} {shape=} {dtype=} {array_received}"
                    )
                self.raw_message_queue.put(Event(message, array_received))

            except Exception as e:
                logger.error(e)
                if message:
                    logger.exception(f"Error dealing with {message=}")

    def stop(self):
        self.stop = True
