import logging
import os
import threading

import typer
from tiled.client import from_uri

from .labview import LabviewListener
from .log_utils import setup_logger
from .processor import monitor_runs
from .result_publisher import XPSResultPublisher

app = typer.Typer()


@app.command()
def listen(
    zmq_pub_address: str = "tcp://127.0.0.1",
    zmq_pub_port: int = 5555,
    log_level="INFO",
    tiled_uri="http://localhost:8000",
    tiled_token=None,
) -> None:
    logger = logging.getLogger(__name__)
    setup_logger(logger)
    logger.setLevel(log_level.upper())
    logger.debug("DEBUG LOGGING SET")
    logger.info(f"zmq_pub_address: {zmq_pub_address}")
    logger.info(f"zmq_pub_port: {zmq_pub_port}")

    if tiled_token is None:
        tiled_token = os.getenv("TILED_SINGLE_USER_API_KEY")
    tiled_client = from_uri(tiled_uri, api_key=tiled_token)
    if tiled_client.get("runs") is None:
        tiled_client.create_container("runs")
    runs_node = tiled_client["runs"]
    XPSResultPublisher()
    LabviewListener(zmq_pub_address, zmq_pub_port)

    thread = threading.Thread(
        target=monitor_runs, name="ResultProcessingThread", args=(runs_node,)
    )
    thread.daemon = True
    thread.start()
    thread.join()


if __name__ == "__main__":
    app()
