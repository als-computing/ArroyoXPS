import time
from uuid import uuid4

import numpy as np
import zmq

IMAGE_METADATA = {"Frame Number": 0, "Width": 1000, "Height": 100, "Type": "I32"}


class RandomLabViewSimulator:
    def __init__(
        self, zmq_pub_address: str = "tcp://127.0.0.1", zmq_pub_port: int = 5555
    ):
        self.ctx = zmq.Context()
        self.socket = self.ctx.socket(zmq.PUB)
        self.socket.bind(f"{zmq_pub_address}:{zmq_pub_port}")

    def _send_image(self, image: np.ndarray):
        self.socket.send(image)

    def start(self, sleep_interval: int = 5):
        while True:
            image_metadata = IMAGE_METADATA
            image = np.random.randint(
                0,
                2000,
                size=(IMAGE_METADATA["Width"], IMAGE_METADATA["Height"]),
                dtype=np.int32,
            )
            start = {"start": {"scan_name": f"test_scan{uuid4()}"}}
            self.socket.send_json(start)
            print(start)
            num_frames = 100
            for i in range(num_frames):
                image_metadata["Frame Number"] = i
                self.socket.send_json({"event": image_metadata})
                self._send_image(image.byteswap().newbyteorder())
                time.sleep(0.1)
            stop = {"stop": {"num_frames": num_frames}}
            self.socket.send_json(stop)
            print(stop)
            time.sleep(sleep_interval)

    def finish(self):
        self.socket.close()
        self.ctx.term()


class LabViewSimulator:
    def __init__(
        self,
        zmq_pub_address: str = "tcp://127.0.0.1",
        zmq_pub_port: int = 5555,
        pickle_dir: str = "./sample_data/scan1"
    ):
        self.ctx = zmq.Context()
        self.socket = self.ctx.socket(zmq.PUB)
        self.socket.bind(f"{zmq_pub_address}:{zmq_pub_port}")
        self.pickle_dir = pickle_dir

    def _send_image(self, image: np.ndarray):
        self.socket.send(image)

    def start(self, sleep_interval: int = 5):
        import glob
        import pickle
        file_paths = glob.glob(f"{self.pickle_dir}/*.pickle")
        for file_path in file_paths:
            with open(file_path, "rb") as file:
                data = pickle.load(file)
                self.socket.send(data)
    
    def finish(self):
        self.socket.close()
        self.ctx.term()


if __name__ == "__main__":
    simulator = LabViewSimulator()
    print("starting labview simulator")
    simulator.start()
    simulator.finish()
    print("Publisher labview simulator.")
