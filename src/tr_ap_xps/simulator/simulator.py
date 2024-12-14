import logging
import time
from enum import Enum

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
    "Rectangle": {"Left": 148, "Top": 385, "Right": 1279, "Bottom": 654, "Rotation": 0},
    "data_type": "U8",
    "dt": 0.0820741786426572,
    "Photon Energy": 3999.99740398402,
    "Binding Energy": 90,
    "File Ver": "1.0.0",
}

stop_example = {
    "msg_type": "stop",
    "Num Frames": 1000,
}

event_example = {"msg_type": "event", "Frame Number": 0}


class RandomLabViewSimulator:
    def __init__(
        self,
        zmq_socket: zmq.Socket,
        scan_pause: int,
        num_frames: int = 5,
        repeat: bool = False,
    ):
        self.zmq_socket = zmq_socket
        self.scan_pause = scan_pause
        self.num_frames = num_frames
        self.repeat = repeat

    def _send_image(self, image: np.ndarray):
        self.zmq_socket.send(image)

    def start(self):
        time.sleep(
            1
        )  # pause to let clients connect...without this the first message is lost
        while True:
            self.zmq_socket.send_json(start_example)
            progress_bar = tqdm.tqdm(
                total=self.num_frames, desc="Sending frames", unit=" "
            )
            rectangle = start_example["Rectangle"]
            height = rectangle["Bottom"] - rectangle["Top"]
            width = rectangle["Right"] - rectangle["Left"]
            for i in range(self.num_frames):
                event_example["Frame Number"] = i
                self.zmq_socket.send_json(event_example)
                self.zmq_socket.send(
                    np.random.randint(0, 255, (width, height), dtype=np.uint8)
                )
                progress_bar.update(1)
                time.sleep(0.01)
            stop_example["Number of Frames"] = self.num_frames
            self.zmq_socket.send_json(stop_example)
            logger.info(
                f"finished sending messages pausing for {self.scan_pause} seconds"
            )
            if not self.repeat:
                break
            time.sleep(self.scan_pause)
            progress_bar.close()

    def finish(self):
        self.zmq_socket.close()


class LabViewPickleSimulator:
    def __init__(self, zmq_socket: zmq.Socket, pickle_dir: str, repeat: bool = False):
        self.socket = zmq_socket
        self.pickle_dir = pickle_dir
        self.repeat = repeat

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
            if not self.repeat:
                break
            time.sleep(5)

    def finish(self):
        self.socket.close()
        self.ctx.term()


class SimType(Enum):
    h5 = "h5"
    random = "random"


@app.command()
def start(
    zmq_pub_address: str = "tcp://*",
    zmq_pub_port: int = 5555,
    log_level: str = "DEBUG",
    repeat: bool = True,
    scan_pause: int = 5,
    num_frames: int = 1000,
    sim_type: SimType = SimType.random,
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
    simulator = None
    # simulator = LabViewPickleSimulator(socket, pickle_dir)
    match sim_type:
        case SimType.h5:
            simulator = LabViewPickleSimulator(socket, "sample_dir", repeat=repeat)
        case SimType.random:
            simulator = RandomLabViewSimulator(
                socket, scan_pause, num_frames, repeat=repeat
            )

    print("starting labview simulator")
    simulator.start()
    simulator.finish()
    print("Publisher labview simulator.")


if __name__ == "__main__":
    app()
