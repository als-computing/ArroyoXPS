import logging
from dataclasses import dataclass

import zmq
import zmq.asyncio

logger = logging.getLogger("ws-publisher.result_subscriber")


@dataclass
class ResultData:
    result_info: dict
    raw: bytes
    fitted: bytes
    vfft: bytes
    ifft: bytes
    # sum: bytes


class ZMQSubscriber:
    def __init__(self, topic, zmq_url):
        self.topic = topic
        self.zmq_url = zmq_url
        self.ctx = zmq.asyncio.Context()
        self.socket = self.ctx.socket(zmq.SUB)
        self.socket.connect(self.zmq_url)
        self.socket.setsockopt_string(zmq.SUBSCRIBE, self.topic)

        logger.info(f"listening for results on {zmq_url=} with {topic=}")

    async def receive_message(self):
        try:
            result_info = await self.socket.recv_json()
            integrated_frame = await self.socket.recv()
            detected_peaks = await self.socket.recv_json()
            vfft = await self.socket.recv()
            ifft = await self.socket.recv()
            # sum = await self.socket.recv()

            return ResultData(
                result_info=result_info,
                raw=integrated_frame,
                fitted=detected_peaks,
                vfft=vfft,
                ifft=ifft,
                # sum=sum
            )
        except Exception as e:
            logger.exception(e)


subscriber = ZMQSubscriber("", "tcp://processor:5556")
