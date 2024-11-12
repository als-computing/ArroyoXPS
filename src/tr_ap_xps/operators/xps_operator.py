import asyncio
import logging

from arroyo.operator import Operator
from arroyo.schemas import Message
from tiled.client import node

from ..pipeline.xps_processor import timer, XPSProcessor
from ..schemas import XPSRawEvent, XPSStart, XPSResultStop

logger = logging.getLogger(__name__)


class XPSOperator(Operator):
    """
    XPSOperator is responsible for handling XPS-related messages and processing frames.
  
    """

    def __init__(self) -> None:
        self.xps_processor = None

    async def process(self, message: Message) -> None:
        """
        Asynchronously handles different types of XPS messages. Handles the lifecycle of an XPSProcessor,
        which is tied to the start and end of a run.

        Args:
            message (Message): The message to be processed. It can be one of the following types:
                - XPSStart: Initializes the XPSProcessor and publishes the start message.
                - XPSRawEvent: Processes a frame using the XPSProcessor and publishes the result.
                - XPSStop: Finalizes the XPSProcessor and publishes the stop message.

        Returns:
            None
        """
        if isinstance(message, XPSStart):
            timer.reset()
            await self.publish(message)
            self.xps_processor = XPSProcessor(message)

        elif isinstance(message, XPSRawEvent):
            if not self.xps_processor:
                logger.error("Received XPSRawEvent without an active XPSProcessor. Started after labview started?")
                return
            result: XPSRawEvent = await asyncio.to_thread(
                self.xps_processor.process_frame, message
            )
            if result:
                await self.publish(result)

        elif isinstance(message, XPSResultStop):
            message.function_timings = timer.timing_dataframe
            await self.publish(message)
            if self.xps_processor:
                self.xps_processor.finish(message)
            self.xps_processor = None
