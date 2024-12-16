import asyncio
import json
import logging
from typing import Union

import msgpack
import numpy as np
import pandas as pd
import websockets

from arroyo.publisher import Publisher

from .schemas import XPSResult, XPSResultStop, XPSStart

logger = logging.getLogger(__name__)


class XPSWSResultPublisher(Publisher):
    """
    A publisher class for sending XPSResult messages over a web sockets.

    """

    websocket_server = None
    connected_clients = set()
    current_start_message = None

    def __init__(self, host: str = "localhost", port: int = 8001):
        super().__init__()
        self.host = host
        self.port = port

    async def start(
        self,
    ):
        # Use partial to bind `self` while matching the expected handler signature
        server = await websockets.serve(
            self.websocket_handler,
            self.host,
            self.port,
        )
        logger.info(f"Websocket server started at ws://{self.host}:{self.port}")
        await server.wait_closed()

    async def publish(self, message: XPSResult) -> None:
        if self.connected_clients:  # Only send if there are clients connected
            asyncio.gather(
                *(self.publish_ws(client, message) for client in self.connected_clients)
            )

    async def publish_ws(
        self,
        #  client: websockets.client.ClientConnection,
        client,
        message: Union[XPSResult | XPSStart | XPSResultStop],
    ) -> None:
        if isinstance(message, XPSResultStop):
            self.current_start_message = None
            return

        if isinstance(message, XPSStart):
            self.current_start_message = message
            await client.send(json.dumps(message.model_dump()))
            return

        # send basic info
        await client.send(
            json.dumps(
                {
                    # "result_info": message.result_info,
                    "frame_number": message.frame_number,
                }
            )
        )
        # send image data separately to client memory issues
        image_bundle = await asyncio.to_thread(pack_images, message)
        await client.send(image_bundle)

    async def websocket_handler(self, websocket):
        logger.info(f"New connection from {websocket.remote_address}")
        if websocket.request.path != "/simImages":
            logger.info(
                f"Invalid path: {websocket.request.path}, we only support /simImages"
            )
            return
        self.connected_clients.add(websocket)
        try:
            # Keep the connection open and do nothing until the client disconnects
            await websocket.wait_closed()
        finally:
            # Remove the client when it disconnects
            self.connected_clients.remove(websocket)
            logger.info("Client disconnected")


def convert_to_uint8(image: np.ndarray) -> bytes:
    """
    Convert an image to uint8, scaling image
    """
    # scaled = (image - image.min()) / (image.max() - image.min()) * 255
    # return scaled.astype(np.uint8).tobytes()

    image_normalized = (image - image.min()) / (image.max() - image.min())

    # Apply logarithmic stretch
    log_stretched = np.log1p(image_normalized)  # log(1 + x) to handle near-zero values

    # Normalize the log-stretched image to [0, 1] again
    log_stretched_normalized = (log_stretched - log_stretched.min()) / (
        log_stretched.max() - log_stretched.min()
    )

    # Convert to uint8 (range [0, 255])
    image_uint8 = (log_stretched_normalized * 255).astype(np.uint8)
    return image_uint8.tobytes()
    # def convert_to_uint8(image: np.ndarray) -> bytes:
    #     image = image.astype(np.float64)
    #     scaled = np.interp(image, (image.min(), image.max()), (0, 255))
    #     return scaled.astype(np.uint8).tobytes()


def peaks_output(peaks: pd.DataFrame):
    #     [
    # {"x": 235, "h": 433.3: "fwhm": 4334},
    # {"x": 235, "h": 433.3: "f whm": 4334}
    # ]
    peaks.columns = ["x", "h", "fwhm"]
    return peaks.to_dict(orient="records")


def pack_images(message: XPSResult) -> bytes:
    """
    Pack all the images into a single msgpack message
    """
    return msgpack.packb(
        {
            "raw": convert_to_uint8(message.integrated_frames.array),
            "vfft": convert_to_uint8(message.vfft.array),
            "ifft": convert_to_uint8(message.ifft.array),
            "width": message.integrated_frames.array.shape[0],
            "height": message.integrated_frames.array.shape[1],
            "fitted": json.dumps(peaks_output(message.detected_peaks.df)),
        }
    )
