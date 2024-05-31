import logging
import os

import numpy as np
import typer
from tiled.client import from_uri

from .listener import ZMQImageListener
from .log import setup_logger
from .processor import XPSProcessor
from .result_publisher import Result, XPSResultPublisher

app = typer.Typer()

setup_logger()
logger = logging.getLogger("tr-ap-xps.cli")

processor = None  # Declare processor as a global variable


@app.command()
def listen(
    zmq_pub_address: str = "tcp://127.0.0.1",
    zmq_pub_port: int = 5555,
    log_level="INFO",
    tiled_uri="http://localhost:8000",
    tiled_token=None,
) -> None:
    logger.setLevel(log_level.upper())
    logger.debug("DEBUG LOGGING SET")
    logger.info(f"zmq_pub_address: {zmq_pub_address}")
    logger.info(f"zmq_pub_port: {zmq_pub_port}")

    if tiled_token is None:
        tiled_token = os.getenv("TILED_SINGLE_USER_API_KEY")
    tiled_client = from_uri(tiled_uri, api_key=tiled_token)
    if tiled_client.get("runs") == None:
        tiled_client.create_container("runs")
    runs_node = tiled_client["runs"]

    result_publisher = XPSResultPublisher()

    def publish_result(result: Result):
        result_publisher.send_result(result)

    def start_function(data: dict):
        logger.info(f"!!!!!!!!!!!!!!!!!!!!!!start: {data}")
        global processor
        processor = XPSProcessor(publish_result, runs_node, data["scan_name"])

    def event_function(frame_info: dict, image: np.ndarray):
        if processor is None:
            logger.error("Processor not started, ignoring frame.")
            return
        logger.info(f"frame: {frame_info=}")
        processor.process_frame(frame_info, image)

    def stop_function(data: dict):
        if processor is None:
            logger.error("Processor not started, ignoring stop.")
            return
        logger.info(f"stop: {data}")
        processor.finish(data)

    listener = ZMQImageListener(
        start_function, event_function, stop_function, zmq_pub_address, zmq_pub_port
    )
    listener.start()


if __name__ == "__main__":
    app()
