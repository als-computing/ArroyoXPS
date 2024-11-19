import asyncio
import logging
import signal

import typer
from tiled.client import from_uri
from tiled.client.node import Container

from ..config import settings
from ..listeners.labview_listener import XPSLabviewZMQListener, setup_zmq
from ..log_utils import setup_logger
from ..operators.xps_operator import XPSOperator
from ..publishers.tiled_result_publisher import TiledPublisher
from ..publishers.ws_result_publisher import XPSWSResultPublisher

app = typer.Typer()
logger = logging.getLogger("tr_ap_xps")
setup_logger(logger)

app_settings = settings.xps


def tiled_runs_container() -> Container:
    try:
        client = from_uri(app_settings.tiled_uri, api_key=app_settings.tiled_api_key)
        if client.get("runs") is None:  # TODO test case
            client.create_container("runs")
        return client["runs"]
    except Exception as e:
        logger.error(f"Error connecting to Tiled: {e}")


@app.command()
async def listen() -> None:
    try:

        logger.setLevel(app_settings.log_level.upper())
        logger.debug("DEBUG LOGGING SET")
        logger.info(f"lv_zmq_pub_address: {app_settings.lv_zmq_listener.zmq_pub_address}")
        logger.info(f"lv_zmq_pub_address: {app_settings.lv_zmq_listener.zmq_pub_port}")
        logger.info(f"tiled_uri: {app_settings.tiled_uri}")
        logger.info(
            f"tiled_api_key: {'****' if app_settings.tiled_api_key else 'NOT SET!!!'}"
        )

        received_sigterm = {"received": False}  # Define the variable received_sigterm

        # setup websocket server
        operator = XPSOperator()
        ws_publisher = XPSWSResultPublisher(
            host=app_settings.websockets_publisher.host,
            port=app_settings.websockets_publisher.port)
        tiled_pub = TiledPublisher(tiled_runs_container())

        operator.add_publisher(ws_publisher)
        operator.add_publisher(tiled_pub)
        # connect to labview zmq

        lv_zmq_socket = setup_zmq()
        listener = XPSLabviewZMQListener(operator=operator, zmq_socket=lv_zmq_socket)

        # Wait for both tasks to complete
        await asyncio.gather(listener.start(), ws_publisher.start())

        def handle_sigterm(signum, frame):
            logger.info("SIGTERM received, stopping...")
            received_sigterm["received"] = True
            asyncio.create_task(listener.stop())
            asyncio.create_task(ws_publisher.stop())

        # Register the handler for SIGTERM
        signal.signal(signal.SIGTERM, handle_sigterm)
    except Exception as e:
        logger.error(f"Error setting up XPS processor {e}")
        raise e

if __name__ == "__main__":
    asyncio.run(listen())
