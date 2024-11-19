import logging
import time
from uuid import uuid4

import numpy as np
import tqdm
import typer
import zmq

from ..log_utils import setup_logger

# from uuid import uuid4


IMAGE_METADATA = {"Frame Number": 0, "Width": 1000, "Height": 100, "Type": "I32"}

app = typer.Typer(help="Labview frame simulator")

logger = logging.getLogger(__name__)


start_example = {
    "msg_type": "start",
    "Binding Energy (eV)": 5.0,
    "frames_per_cycle": 5,
    "msg_type": "start",
    "scan_name": f"test_scan{uuid4()}",
    "scan_id": "12345",
}

event_example = {
    "msg_type": "event",
    "timestamp": time.time(),
    "Frame Number": 0,
    "Width": 1024,
    "Height": 1024,
    "Type": "U8",
}

stop_example = {
    "msg_type": "stop",
    "F_Trigger": 1,
    "F_Un-Trigger": 2,
    "F_Dead": 3,
    "F_Reset": 4,
    "CCD_nx": 1024,
    "CCD_ny": 768,
    "Pass Energy": 20,
    "Center Energy": 1000,
    "Offset Energy": 0,
    "Lens Mode": "Mode1",
    "Rectangle": {
        "Left": 1,
        "Top": 2,
        "Right": 3,
        "Rotation": 4,
        "Bottom": 5,
    },
    "Notes": "Sample notes",
    "dt": 0.1,
    "Photon Engergy": 1486.6,
    "Binding Energy": 0.0,
    "File Ver": "1.0",
    "Strean": "stream1",
}


class RandomLabViewSimulator:
    def __init__(self, zmq_socket: zmq.Socket, scan_pause: int, num_frames: int = 10000):
        self.zmq_socket = zmq_socket
        self.scan_pause = scan_pause
        self.num_frames = num_frames

    def _send_image(self, image: np.ndarray):
        self.zmq_socket.send(image)

    def start(self, sleep_interval: int = 5):
        time.sleep(5) # pause to let clients connect...without this the first message is lost
        while True:
            self.zmq_socket.send_json(start_example)
            progress_bar = tqdm.tqdm(total=self.num_frames, desc="Sending frames", unit=" ")
            for i in range(self.num_frames):
                event_example["Frame Number"] = i
                self.zmq_socket.send_json(event_example)
                self.zmq_socket.send(
                    np.random.randint(0, 255, (1024, 1024), dtype=np.uint8)
                )
                progress_bar.update(1)
                time.sleep(0.01)
            self.zmq_socket.send_json(stop_example)
            logger.info(f"finished sending messages pausing for {self.scan_pause} seconds")
            time.sleep(self.scan_pause)
            progress_bar.close()

    def finish(self):
        self.zmq_socket.close()


class LabViewPickleSimulator:
    def __init__(self, zmq_socket: zmq.Socket, pickle_dir: str):
        self.socket = zmq_socket
        self.pickle_dir = pickle_dir

    def _send_image(self, image: np.ndarray):
        self.socket.send(image)

    def start(self, sleep_interval: int = 5):
        import glob
        import os
        import pickle

        file_paths = glob.glob(f"{self.pickle_dir}/*.pickle")
        # load messages into memory
        messages = {}
        for file_path in file_paths:
            with open(file_path, "rb") as file:
                data = pickle.load(file)
                file_name = int(os.path.splitext(os.path.basename(file_path))[0])
                messages[file_name] = data

        # sort messages by key
        sorted_messages = dict(sorted(messages.items(), key=lambda x: x[0]))
        num_msgs = len(sorted_messages)
        while True:
            logger.info(f"about to send {num_msgs} messages")
            # loop through each scan message
            for file_name, data in sorted_messages.items():
                logger.debug(f"  {file_name=}")
                self.socket.send(data)
                time.sleep(0.01)
            logger.info(f"send {len(sorted_messages.keys())} message")
            time.sleep(5)
        

    def finish(self):
        self.socket.close()
        self.ctx.term()


@app.command()
def start(
    zmq_pub_address: str = "tcp://*",
    zmq_pub_port: int = 5555,
    log_level: str ="DEBUG",
    scan_pause: int = 600,
    num_frames: int = 1000
) -> None:
    setup_logger(logger)
    logger.setLevel(log_level.upper())
    logger.info(f"{log_level=}")
    logger.debug("DEBUG LOGGING SET")
    logger.info(f"zmq_pub_address: {zmq_pub_address}")
    logger.info(f"zmq_pub_port: {zmq_pub_port}")
    ctx = zmq.Context()
    socket = ctx.socket(zmq.PUB)
    socket.setsockopt(zmq.SNDHWM, 10000) 
    socket.bind(f"{zmq_pub_address}:{zmq_pub_port}")
    logger.info(f"publishing labview simulations {zmq_pub_address}:{zmq_pub_port}")

    # simulator = LabViewPickleSimulator(socket, pickle_dir)
    simulator = RandomLabViewSimulator(socket, scan_pause, num_frames)
    print("starting labview simulator")
    simulator.start()
    simulator.finish()
    print("Publisher labview simulator.")


if __name__ == "__main__":
    app()
