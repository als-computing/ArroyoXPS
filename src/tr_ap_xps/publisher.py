import time

import numpy as np
import zmq

IMAGE_METADATA = {"Frame Number": 39, "Width": 10, "Height": 10, "Type": "I32"}


class ImagePublisher:
    def __init__(
        self, zmq_pub_address: str = "tcp://127.0.0.1", zmq_pub_port: int = 5555
    ):
        self.ctx = zmq.Context()
        self.socket = self.ctx.socket(zmq.PUB)
        self.socket.bind(f"{zmq_pub_address}:{zmq_pub_port}")

    def _send_image(self, image: np.ndarray):
        self.socket.send(image)
        print(f"sent: shape: {image.shape} dtype: {image.dtype}")

    def start(self, sleep_interval: int = 2):
        image = np.random.randint(
            0,
            20000,
            size=(IMAGE_METADATA["Width"], IMAGE_METADATA["Height"]),
            dtype=np.int32,
        )
        while True:
            self._send_image(image)
            self.socket.send_json(IMAGE_METADATA)
            time.sleep(sleep_interval)

    def finish(self):
        self.socket.close()
        self.ctx.term()


if __name__ == "__main__":
    publisher = ImagePublisher()
    print("starting publisher")
    publisher.start()

    # publisher.finish()
    print("Publisher finished.")
