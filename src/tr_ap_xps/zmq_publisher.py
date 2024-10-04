import zmq
from arroyo.publisher import AbstractPublisher

from .schemas import XPSResult


class XPSZMQResultPublisher(AbstractPublisher):
    """
    A publisher class for sending XPSResult messages over a ZeroMQ socket.
    Attributes:
        zmq_socket (zmq.Socket): The ZeroMQ socket used for sending messages.

    """

    def __init__(self, zmq_socket: zmq.Socket):
        self.zmq_socket = zmq_socket

    def publish(self, message: XPSResult) -> None:
        self.socket.send_json(
            {
                "frame_number": message.frame_number,
                "shape": message.integrated_frame.shape,
                "dtype": str(message.integrated_frame.dtype),
            }
        )  # Convert dtype to string
        self.socket.send(message.integrated_frame)
        self.socket.send(message.filtered_integrated_frame)
