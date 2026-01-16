import json
import logging
import uuid

import numpy as np
import msgpack
import zmq.asyncio

from arroyopy.zmq import ZMQListener
from arroyosas.schemas import RawFrameEvent, ImageInfo

from .config import settings
from .schemas import NumpyArrayModel, XPSImageInfo, XPSRawEvent, XPSStart, XPSStop



app_settings = settings.xps_operator

logger = logging.getLogger(__name__)


def setup_zmq():
    ctx = zmq.asyncio.Context()
    lv_zmq_socket = ctx.socket(zmq.SUB)
    lv_zmq_socket.setsockopt(zmq.RCVHWM, 100000)
    logger.info(
        f"binding to: {app_settings.tpx_zmq_listener.zmq_pub_address}:{app_settings.tpx_zmq_listener.zmq_pub_port}"
    )
    lv_zmq_socket.connect(
        f"{app_settings.tpx_zmq_listener.zmq_pub_address}:{app_settings.tpx_zmq_listener.zmq_pub_port}"
    )
    lv_zmq_socket.setsockopt(zmq.SUBSCRIBE, b"")
    return lv_zmq_socket


class XPSTimepixZMQListener(ZMQListener):
    stop_signal = False

    async def start(self):
        logger.info("Listener started")
        current_image_info: XPSImageInfo = None
        while True:
            try:
                if self.stop_signal:
                    logger.info("Stopping listener.")
                    break
                metadata_msg_packed = await self.zmq_socket.recv()
                raw_message = await self.zmq_socket.recv()
                # print(raw_message[0:300])
                try:
                    metadata = msgpack.unpackb(metadata_msg_packed)
                except Exception as e:
                    logger.error(f"Error unpacking message: {e}")
                    continue


                # Must be an event with an image
                if logger.getEffectiveLevel() == logging.DEBUG:
                    logger.debug(f"event: {metadata.keys()}")
           
                await self.operator.process(
                    self._build_event(raw_message, metadata)
                )
                logger.debug("event processed")
            except Exception as e:
                logger.error(e)

    @staticmethod
    def _build_event(
        image: bytes,
        metadata: dict,

    ) -> XPSRawEvent:
        shape = tuple(metadata["shape"])
        dtype = metadata["dtype"]

        image_info = XPSImageInfo(
            frame_number=0,
            width=shape[0],
            height=shape[1],
            data_type=dtype
        )

        array_received = np.frombuffer(image, dtype=dtype).reshape(shape)
        image_info.frame_number = metadata.get("flush_number")
        return XPSRawEvent(
            image=NumpyArrayModel(array=array_received), image_info=image_info
        )


if __name__ == "__main__":
    from .log_utils import setup_logger  # noqa: F401

    class DummyOperator:
        async def process(self, event: XPSRawEvent):
            logger.info(
                f"Dummy operator received event with image shape: {event.image.array.shape}"
            )


    setup_logger(logger)
    zmq_socket = setup_zmq()
    listener = XPSTimepixZMQListener(zmq_socket=zmq_socket, operator=DummyOperator())
    import asyncio
    asyncio.run(listener.start())