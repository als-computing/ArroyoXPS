import logging

import zmq
import zmq.asyncio

from ..model import Result

logger = logging.getLogger(__name__)


class ZMQSubscriber:
    def __init__(self, topic, zmq_url):
        self.topic = topic
        self.zmq_url = zmq_url
        self.ctx = zmq.asyncio.Context()
        self.socket = self.ctx.socket(zmq.SUB)
        self.socket.connect(self.zmq_url)
        self.socket.setsockopt_string(zmq.SUBSCRIBE, self.topic)

    async def receive_message(self):
        try:
            result_info = await self.socket.recv_json()
            integrated_frame = await self.socket.recv()
            detected_peaks = await self.socket.recv()
            vfft = await self.socket.recv()
            ifft = await self.socket.recv()
            sum = await self.socket.recv()

            return Result(
                result_info["frame_number"],
                integrated_frame,
                detected_peaks,
                vfft,
                ifft,
                sum,
            )
        except Exception as e:
            logger.exception(e)


subscriber = ZMQSubscriber("", "tcp://localhost:5556")
