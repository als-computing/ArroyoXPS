import time

import numpy as np
import zmq


class ImagePublisher:
    def __init__(
        self, zmq_pub_address: str = "tcp://127.0.0.1", zmq_pub_port: int = 5555
    ):
        self.ctx = zmq.Context()
        self.socket = self.ctx.socket(zmq.PUB)
        self.socket.bind(f"{zmq_pub_address}:{zmq_pub_port}")

    def _send_image(self, image: np.ndarray):
        self.socket.send(image)
        self.socket.send_pyobj(image.shape)
        self.socket.send_pyobj(image.dtype)
        print(f"sent: shape: {image.shape} dtype: {image.dtype}")

    def start(self, sleep_interval: int = 2):
        image = np.array([[1, 2, 3], [4, 5, 6]], dtype=">u2", order="C")
        # image = np.random.rand(1024, 1024)
        while True:
            self._send_image(image)
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
