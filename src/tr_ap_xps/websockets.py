import asyncio
import base64
import io
import json
import logging
from typing import Union

import numpy as np
import pandas as pd
import websockets
from arroyo.publisher import Publisher
from PIL import Image

from .schemas import XPSResult, XPSResultStop, XPSStart

logger = logging.getLogger(__name__)


class XPSWSResultPublisher(Publisher):
    """
    A publisher class for sending XPSResult messages over a web sockets.

    """

    websocket_server = None
    connected_clients = set()

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
            return

        if isinstance(message, XPSStart):
            await client.send(json.dumps(message.model_dump()))
            return

        raw = buffer_to_jpeg(message.integrated_frames.array)
        ifft = buffer_to_jpeg(message.ifft.array)
        vfft = buffer_to_jpeg(message.vfft.array)

        # sum_json = df_to_json(result.sum)
        detected_peaks = json.dumps(peaks_output(message.detected_peaks.df))

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
        await client.send(json.dumps({"raw": raw}))
        await client.send(json.dumps({"fitted": detected_peaks}))
        await client.send(json.dumps({"vfft": vfft}))
        await client.send(json.dumps({"ifft": ifft}))

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


def buffer_to_jpeg(arra_: np.ndarray):
    if arra_.dtype != np.uint8:
        arra_ = (arra_ * 255).astype(np.uint8)

    img = Image.fromarray(arra_, "L")
    # Convert image to base64
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str


def peaks_output(peaks: pd.DataFrame):
    #     [
    # {"x": 235, "h": 433.3: "fwhm": 4334},
    # {"x": 235, "h": 433.3: "f whm": 4334}
    # ]
    peaks.columns = ["x", "h", "fwhm"]
    return peaks.to_dict(orient="records")
