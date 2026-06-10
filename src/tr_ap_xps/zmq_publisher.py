import logging

import msgpack
import zmq
import zmq.asyncio
from arroyopy.publisher import Publisher
from zmq.asyncio import Context, Socket

from arroyosas.schemas import RawFrameEvent, SASMessage, SASStart, SASStop

logger = logging.getLogger(__name__)


class ZMQFramePublisher(Publisher):
    def __init__(self, zmq_socket: Socket):
        self.zmq_socket = zmq_socket

    async def publish(self, message: SASMessage) -> None:
        logger.debug(f"Publishing message: {message.msg_type}")
        if isinstance(message, SASStart) or isinstance(message, SASStop):
            message = msgpack.packb(message.model_dump(), use_bin_type=True)
            await self.zmq_socket.send(message)
            return
        if isinstance(message, RawFrameEvent):
            message = message.model_dump()
            message = msgpack.packb(message, use_bin_type=True)
            await self.zmq_socket.send(message)
        else:
            logger.warning(f"Unknown message type: {type(message)}")

    @classmethod
    def from_settings(cls, settings) -> "ZMQFramePublisher":
        context = Context()
        zmq_socket = context.socket(zmq.PUB)
        zmq_socket.bind(settings.address)
        logger.info(f"##### Publishing frames to {settings.address}")
        return cls(zmq_socket)


def create_zmq_frame_publisher(zmq_address: str) -> ZMQFramePublisher:
    context = Context()
    zmq_socket = context.socket(zmq.PUB)
    zmq_socket.bind(zmq_address)
    logger.info(f"##### Publishing frames to {zmq_address}")
    return ZMQFramePublisher(zmq_socket)
