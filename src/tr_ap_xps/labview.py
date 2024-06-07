import json
import logging
import signal
import threading
from uuid import uuid4

import numpy as np
import zmq

from .model import Event, Start, Stop
from .shared_queue import raw_message_queue

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
        zmq_pub_address: str = "tcp://127.0.0.1",
        zmq_pub_port: int = 5555,
    ):
        self.zmq_pub_address = zmq_pub_address
        self.zmq_pub_port = zmq_pub_port
        self.stop = False
        self.thread = threading.Thread(target=self.listen, name="LabviewListenerThread")
        self.thread.daemon = True
        self.thread.start()

    def listen(self):
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
                except Exception:
                    image = message
                    message_json = None

                if message_json:
                    # logger.info(f"{message=}")
                    message_type = message_json["msg_type"]
                    if message_type == "start":
                        message_json[
                            "scan_name"
                        ] = f"temporary scan name{uuid4()}"  # temporary
                        raw_message_queue.put(Start(message_json))

                        logger.info(f"start: {message}")
                        continue
                    if message_type == "metadata":
                        raw_message_queue.put(Stop(message_json))
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
                    if raw_message_queue.qsize() > 100:
                        raw_message_queue.get()  # Remove oldest item from the queue
                    raw_message_queue.put(Event(frame_num, image_info, array_received))
                    frame_num += 1

            except Exception as e:
                logger.error(e)

    def stop(self):
        self.stop = True
