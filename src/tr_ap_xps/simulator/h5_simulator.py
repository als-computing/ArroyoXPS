import logging
import time
from uuid import uuid4

import h5py
import json
import numpy as np
import tqdm
import typer
import zmq

from ..log_utils import setup_logger

# from uuid import uuid4


app = typer.Typer(help="Labview H5 frame simulator")

logger = logging.getLogger(__name__)

event_msg = {
    "msg_type": "event",
    "timestamp": time.time(),
    "Frame Number": 0,
    "Width": 1024,
    "Height": 1024,
    "Type": "U8",
}

stop_msg = {
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

class H5LabViewSimulator:
    def __init__(self, file: str, scan: str, zmq_socket: zmq.Socket, scan_pause: int, num_frames: int = 10000):
        self.file = file
        self.scan = scan
        self.zmq_socket = zmq_socket
        self.scan_pause = scan_pause

    def _send_image(self, image: np.ndarray):
        self.zmq_socket.send(image)

    def start(self, sleep_interval: int = 5):
        time.sleep(5) # pause to let clients connect...without this the first message is lost
        with h5py.File(self.file, "r") as file:
            group = file[self.scan]
            metadata = json.loads(group["Metadata"][()])
            metadata["msg_type"] = "start"
            metadata["scan_name"] = self.scan + str(uuid4())
            metadata["Binding Energy (eV)"] = 22
            metadata["frames_per_cycle"] = 10
            logger.info(metadata)

            self.zmq_socket.send_json(metadata)
      
            frames = group["Frame"]
            event_msg["Width"] = frames.shape[1]
            event_msg["Height"] = frames.shape[2]
            num_frames = frames.shape[0]
            progress_bar = tqdm.tqdm(total=num_frames, desc="Sending frames", unit=" ")
            for i in range(num_frames):
                event_msg["Frame Number"] = i
                self.zmq_socket.send_json(event_msg)
                self.zmq_socket.send(frames[i])
                progress_bar.update(1)
    
            self.zmq_socket.send_json(stop_msg)
            # logger.info(f"finished sending messages pausing for {self.scan_pause} seconds")
            # time.sleep(self.scan_pause)
            progress_bar.close()

    def finish(self):
        self.zmq_socket.close()




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
    simulator = H5LabViewSimulator("/home/dmcreynolds/data/bl931/TRS_deltaV.h5", "00014", socket, scan_pause)
    print("starting labview simulator")
    simulator.start()
    simulator.finish()
    print("Publisher labview simulator.")


if __name__ == "__main__":
    app()
