import asyncio
import logging

import typer
import zmq.asyncio
from tiled.client import from_uri
from tiled.client.node import Node

from .config import settings
from .labview_listener import XPSLabviewZMQListener
from .log_utils import setup_logger
from .operator import XPSOperator
from .publish.websocket_publisher import XPSWSResultPublisher

app = typer.Typer()
logger = logging.getLogger("tr-ap-xps.cli")
setup_logger(logger)
processor = None  # Declare processor as a global variable

app_settings = settings.zmq_xps


@app.command()
async def listen() -> None:
    logger.setLevel(app_settings.log_level.upper())
    logger.debug("DEBUG LOGGING SET")
    logger.info(f"lv_zmq_pub_address: {app_settings.lv_zmq_pub_address}")
    logger.info(f"lv_zmq_pub_address: {app_settings.lv_zmq_pub_port}")
    logger.info(f"tiled_uri: {app_settings.tiled_uri}")
    logger.info(f"tiled_token: {'****' if app_settings.tiled_token else 'NOT SET!!!'}")
    tiled_client = from_uri(app_settings.tiled_uri, api_key=app_settings.tiled_token)
    runs_node: Node = tiled_client["runs"]

    # setup websocket server
    ws_publisher = XPSWSResultPublisher()

    operator = XPSOperator(ws_publisher, runs_node)
    operator.add_publisher(ws_publisher)

    # connect to labview zmq
    ctx = zmq.asyncio.Context()
    lv_zmq_socket = ctx.socket(zmq.SUB)
    logger.info(
        f"binding to: {app_settings.lv_zmq_pub_address}:{app_settings.lv_zmq_pub_port}"
    )
    lv_zmq_socket.connect(
        f"{app_settings.lv_zmq_pub_address}:{app_settings.lv_zmq_pub_port}"
    )
    lv_zmq_socket.setsockopt(zmq.SUBSCRIBE, b"")
    listener = XPSLabviewZMQListener(operator=operator, zmq_socket=lv_zmq_socket)

    # Wait for both tasks to complete
    await asyncio.gather(listener.start(), ws_publisher.start_server())


if __name__ == "__main__":
    asyncio.run(listen())
