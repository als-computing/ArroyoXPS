import asyncio

import websockets
from arroyo.publisher import AbstractPublisher

from ..schemas import XPSResult


class XPSWSResultPublisher(AbstractPublisher):
    """
    XPSWSResultPublisher is a class that handles WebSocket communication for publishing XPS results.

    Attributes:
        websocket (WebSocket): The WebSocket connection used for communication.

    """

    websocket = None

    async def publish(self, message: XPSResult) -> None:
        if self.websocket:  # websocket isn't set until a client connects
            await self.websocket.send(message.model_dump_json())
        print("ldsfjlsdfjsdlkfj")

    async def receive(self, websocket) -> None:
        async for message in websocket:
            print(message)

    async def set_websocket(self, websocket):
        # called when a client connects
        self.websocket = websocket

    async def start_server(self):
        async with websockets.serve(self.set_websocket, "localhost", 8765):
            print("WebSocket server started on ws://localhost:8765")
            await asyncio.Future()  # Run forever
