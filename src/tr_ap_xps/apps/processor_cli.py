import asyncio
import logging
import signal

from tiled.client import from_uri
from tiled.client.node import Container
import typer

from ..config import settings
from ..listeners.labview_listener import XPSLabviewZMQListener, setup_zmq
from ..log_utils import setup_logger
from ..operators.xps_operator import XPSOperator
from ..publishers.ws_result_publisher import XPSWSResultPublisher
from ..publishers.tiled_result_publisher import TiledPublisher

app = typer.Typer()
logger = logging.getLogger("tr_ap_xps")
setup_logger(logger)

app_settings = settings.xps

def signal_handler(sig, frame):
    logger.info("SIGINT received, stopping...")
    asyncio.create_task(processor.stop())

def tiled_runs_Container() -> Container:
    client = from_uri(app_settings.tiled_uri, api_key=app_settings.tiled_api_key)
    if client.get("runs") is None:  #TODO test case
        client.create_container("runs")
    return client["runs"]


@app.command()
async def listen() -> None:
    breakpoint()
    logger.setLevel(app_settings.log_level.upper())
    logger.debug("DEBUG LOGGING SET")
    logger.info(f"lv_zmq_pub_address: {app_settings.lv_zmq_listener.zmq_pub_address}")
    logger.info(f"lv_zmq_pub_address: {app_settings.lv_zmq_listener.zmq_pub_port}")
    logger.info(f"tiled_uri: {app_settings.tiled_uri}")
    logger.info(f"tiled_api_key: {'****' if app_settings.tiled_api_key else 'NOT SET!!!'}")
   
    received_sigterm = {"received": False}  # Define the variable received_sigterm


    # setup websocket server
    operator = XPSOperator()
    ws_publisher = XPSWSResultPublisher()
    tiled_pub = TiledPublisher(tiled_runs_Container())
    
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

if __name__ == "__main__":
    asyncio.run(listen())
