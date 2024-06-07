import logging
import os
import queue
import threading
import time

import numpy as np
import typer
import uvicorn
from tiled.client import from_uri, node

from .app import app
from .beamline_events import Event, Start, Stop
from .labview import LabviewListener
from .log import setup_logger
from .processor import XPSProcessor

cli_app = typer.Typer()

setup_logger()
logger = logging.getLogger("tr-ap-xps.cli")

raw_message_queue = queue.Queue()
processed_message_queue = queue.Queue()


def start_listener(listener: LabviewListener):
    listener.start()


def monitor_runs(runs_node: node):
    message = None
    while True:
        try:
            message = raw_message_queue.get(
                timeout=1
            )  # Timeout to prevent indefinite blocking
        except queue.Empty:
            pass
        if not message:
            continue
        try:
            if isinstance(message, Start):
                processor = XPSProcessor(
                    processed_message_queue,
                    runs_node,
                    message.metadata["scan_name"],
                    message.metadata["frame_per_cycle"],
                )

            if isinstance(message, Event):
                result = processor.process_frame(message)
                if isinstance(message, Event):
                    result = processor.process_frame(message)
                    if processed_message_queue.qsize() > 100:
                        processed_message_queue.get()

                    processed_message_queue.put(result)

            if isinstance(message, Stop):
                processor = None
        except Exception as e:
            logger.error(e)
        time.sleep(0.01)


@cli_app.command()
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
    if tiled_client.get("runs") is None:
        tiled_client.create_container("runs")
    runs_node = tiled_client["runs"]

    labview_listener = LabviewListener(
        raw_message_queue, zmq_pub_address=zmq_pub_address, zmq_pub_port=zmq_pub_port
    )
    labview_thread = threading.Thread(
        name="LabviewListenerThread", target=start_listener, args=(labview_listener,)
    )
    labview_thread.start()

    processor_thread = threading.Thread(
        name="ProcessorThread", target=monitor_runs, args=(runs_node,)
    )
    processor_thread.start()
    uvicorn.run("tr_ap_xps.app:app", host="0.0.0.0", port=8001, reload=True)


if __name__ == "__main__":
    cli_app()
