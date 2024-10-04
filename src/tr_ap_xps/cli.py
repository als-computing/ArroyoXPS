import logging

import typer

from .config import settings

# from .labview_listener import XPSLabviewZMQListener
from .log import setup_logger

# from .operator import XPSOperator
# from .schemas import XPSRawEvent
# from .zmq_publisher import XPSZMQResultPublisher

app = typer.Typer()


setup_logger()
logger = logging.getLogger("tr-ap-xps.cli")

processor = None  # Declare processor as a global variable

app_settings = settings.zmq_xps


@app.command()
def listen() -> None:
    logger.setLevel(app_settings.log_level.upper())
    logger.debug("DEBUG LOGGING SET")
    logger.info(f"lv_zmq_pub_address: {app_settings.lv_zmq_pub_address}")
    logger.info(f"lv_zmq_pub_address: {app_settings.lvzmq_pub_port}")

    # tiled_client = from_uri(settings.tiled_uri, api_key=app_settings.tiled_token)
    # runs_node = tiled_client["runs"]

    # result_publisher = XPSZMQResultPublisher()

    # publisher = XPSZMQResultPublisher()
    # operator = XPSOperator()
    # listener = XPSLabviewZMQListener(
    #     start_function, event_function, stop_function, zmq_pub_address, zmq_pub_port
    # )
    # listener.start()


if __name__ == "__main__":
    app()
