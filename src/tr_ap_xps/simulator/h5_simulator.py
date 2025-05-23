import json
import logging
import time
from uuid import uuid4

import h5py
import numpy as np
import tqdm
import typer
import zmq

from ..log_utils import setup_logger
from .simulator import stop_example

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


class H5LabViewSimulator:
    def __init__(
        self,
        file: str,
        scan: str,
        zmq_socket: zmq.Socket,
        scan_pause: int,
        repeat_scans: int,
        single_scan_mode: bool,
    ):
        self.file = file
        self.scan = scan
        self.zmq_socket = zmq_socket
        self.scan_pause = scan_pause
        self.repeat_scans = repeat_scans
        self.single_scan_mode = single_scan_mode

    def _send_image(self, image: np.ndarray):
        self.zmq_socket.send(image)

    def start(self, scan_pause: int = 5):
        time.sleep(
            5
        )  # pause to let clients connect...without this the first message is lost
        while True:
            with h5py.File(self.file, "r") as file:
                frame_number = 1
                group = file[self.scan]
                metadata = json.loads(group["Metadata"][()])
                logger.info(metadata)
                frames = group["Frame"]
                metadata["msg_type"] = "start"
                metadata["scan_name"] = self.scan + str(uuid4())
                metadata["data_type"] = "U8"
                self.zmq_socket.send_json(metadata)
                event_msg["Width"] = frames.shape[1]
                event_msg["Height"] = frames.shape[2]
                num_frames = frames.shape[0]
                progress_bar = tqdm.tqdm(
                    total=num_frames, desc="Sending frames", unit=" "
                )

                for _ in range(self.repeat_scans):  # repeat the scan
                    logging.info(f"repeating scan {self.repeat_scans} times")
                    for i in range(num_frames):
                        event_msg["Frame Number"] = frame_number
                        frame_number += 1
                        self.zmq_socket.send_json(event_msg)
                        self.zmq_socket.send(frames[i])
                        progress_bar.update(1)

                self.zmq_socket.send_json(stop_example)
                logger.info(stop_example)
                progress_bar.close()
            logger.info(
                f"finished sending messages pausing for {self.scan_pause} seconds"
            )
            if self.single_scan_mode:
                break
            time.sleep(scan_pause)

    def finish(self):
        self.zmq_socket.close()


@app.command()
def start(
    file: str = typer.Argument("sample_data/trs_small.h5", help="H5 file to read"),
    group: str = typer.Argument("00014", help="H5 group to read"),
    zmq_pub_address: str = "tcp://*",
    zmq_pub_port: int = 5555,
    log_level: str = "DEBUG",
    scan_pause: int = 5,
    single_scan_mode: bool = True,
    repeat_scans: int = typer.Option(
        50, help="Number of times to repeat data from a scan as a full scan"
    ),
) -> None:
    setup_logger(logger)
    logger.setLevel(log_level.upper())
    logger.info(f"{log_level=}")
    logger.info(f"{file=}")
    logger.info(f"{group=}")
    logger.debug("DEBUG LOGGING SET")
    logger.info(f"zmq_pub_address: {zmq_pub_address}")
    logger.info(f"zmq_pub_port: {zmq_pub_port}")
    ctx = zmq.Context()
    socket = ctx.socket(zmq.PUB)
    socket.setsockopt(zmq.SNDHWM, 10000)
    socket.bind(f"{zmq_pub_address}:{zmq_pub_port}")
    logger.info(f"publishing labview simulations {zmq_pub_address}:{zmq_pub_port}")

    # simulator = LabViewPickleSimulator(socket, pickle_dir)
    simulator = H5LabViewSimulator(
        file, group, socket, scan_pause, repeat_scans, single_scan_mode
    )
    print("starting labview simulator")
    simulator.start()
    simulator.finish()
    print("Publisher labview simulator.")


if __name__ == "__main__":
    app()
