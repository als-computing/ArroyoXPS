import logging
import queue
import threading
import time

import typer

from ..log_utils import setup_logger
from ..model import Event, Start, Stop
from ..processor.processor import XPSProcessor
from .lv_listener import LabviewListener
from .result_publisher import XPSResultPublisher
from .shared_queue import processed_message_queue, raw_message_queue

app = typer.Typer()

logger = logging.getLogger("processor")
setup_logger(logger)


@app.command()
def listen(
    lv_zmq_pub_address: str = "tcp://simulator",
    lv_zmq_pub_port: int = 5555,
    result_zmq_pub_address: str = "tcp://0.0.0.0",
    result_zmq_pub_port: int = 5554,
    log_level="INFO",
) -> None:
    logger.setLevel(log_level.upper())
    logger.debug("DEBUG LOGGING SET")
    logger.info(f"{lv_zmq_pub_address=}")
    logger.info(f"{lv_zmq_pub_port=}")
    logger.info(f"{result_zmq_pub_address=}")
    logger.info(f"{result_zmq_pub_port=}")
    # if tiled_token is None:
    #     tiled_token = os.getenv("TILED_SINGLE_USER_API_KEY")

    # try:
    #     tiled_client = from_uri(tiled_uri, api_key=tiled_token)
    #     if tiled_client.get("runs") is None:
    #         tiled_client.create_container("runs")
    #     runs_node = tiled_client["runs"]
    # except Exception as e:
    #     logger.exception(e, "Cannot talk to Tiled. Getting out")

    XPSResultPublisher(result_zmq_pub_address, result_zmq_pub_port)
    LabviewListener(0, lv_zmq_pub_port)

    thread = threading.Thread(target=monitor_runs, name="ResultProcessingThread")
    thread.daemon = True
    thread.start()
    thread.join()


def monitor_runs():
    message = None
    processor = None
    logger.info("Listening for messages from raw_message_queue")
    while True:
        try:
            message = raw_message_queue.get(
                timeout=1
            )  # Timeout to prevent indefinite blocking
        except queue.Empty:
            continue

        try:
            if isinstance(message, Start):
                processor = XPSProcessor(
                    message.metadata["scan_name"],
                    message.metadata["frame_per_cycle"],
                )
                continue

            if isinstance(message, Event):
                if not processor:
                    logger.error("Error. Was scan start before we were listening?")
                    continue
                result = processor.process_frame(message)
                if result:
                    if processed_message_queue.qsize() > 100:
                        processed_message_queue.get()
                    processed_message_queue.put(result)
                continue
            if isinstance(message, Stop):
                if processor:
                    processor.finish(message)
                processor = None
        except Exception as e:
            logger.exception(e)
        time.sleep(0.01)


if __name__ == "__main__":
    app()
