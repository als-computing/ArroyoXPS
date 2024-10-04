import logging
import threading

import typer

from ..log_utils import setup_logger
from .lv_listener import LabviewListener, monitor_runs
from .result_publisher import XPSResultPublisher

app = typer.Typer()

logger = logging.getLogger(__name__)
setup_logger(logger)


@app.command()
def listen(
    lv_zmq_pub_address: str = "tcp://simulator",
    lv_zmq_pub_port: int = 5555,
    result_zmq_pub_address: str = "tcp://0.0.0.0",
    result_zmq_pub_port: int = 5556,
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
    LabviewListener(lv_zmq_pub_address, lv_zmq_pub_port)

    thread = threading.Thread(target=monitor_runs, name="ResultProcessingThread")
    thread.daemon = True
    thread.start()
    thread.join()


if __name__ == "__main__":
    app()
