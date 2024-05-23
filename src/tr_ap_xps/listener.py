import logging
import signal

import numpy as np
import typer
import zmq

from .log import setup_logger

app = typer.Typer()
setup_logger()

logger = logging.getLogger("tr-ap-xps.listener")

received_sigterm = {"received": False}  # Define the variable received_sigterm


def handle_sigterm(signum, frame):
    logger.info("SIGTERM received, stopping...")
    received_sigterm["received"] = True


# Register the handler for SIGTERM
signal.signal(signal.SIGTERM, handle_sigterm)


class ZMQImageDispatcher:
    def __init__(
        self,
        zmq_pub_address: str = "tcp://127.0.0.1",
        zmq_pub_port: int = 5555,
        function: callable = None,
    ):
        self.zmq_pub_address = zmq_pub_address
        self.zmq_pub_port = zmq_pub_port
        self.function = function
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
                buffer = socket.recv()
                image_info = socket.recv_json()
                shape = (image_info["Width"], image_info["Width"])
                array_received = np.frombuffer(buffer, dtype=np.int32).reshape(shape)
                logger.debug(
                    f"received: shape: {shape} dtype: {np.int32} array: {array_received}"
                )
                if self.function:
                    self.function(array_received)
            except Exception as e:
                logger.error(e)
                if image_info:
                    logger.error(f"Error dealing with {image_info=}")

    def stop(self):
        self.stop = True


@app.command()
def listen(
    zmq_pub_address: str = "tcp://127.0.0.1",
    zmq_pub_port: int = 5555,
    log_level="INFO",
) -> None:
    logger.setLevel(log_level.upper())
    logger.debug("DEBUG LOGGING SET")
    logger.info(f"zmq_pub_address: {zmq_pub_address}")
    logger.info(f"zmq_pub_port: {zmq_pub_port}")
    dispatcher = ZMQImageDispatcher(zmq_pub_address, zmq_pub_port)
    dispatcher.start()


if __name__ == "__main__":
    app()
