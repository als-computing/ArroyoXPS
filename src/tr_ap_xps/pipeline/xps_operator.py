import asyncio
import logging

from arroyo.operator import Operator
from arroyo.schemas import Message

from ..schemas import DataFrameModel, XPSRawEvent, XPSResultStop, XPSStart, XPSStop
from ..timing import timer
from .xps_processor import XPSProcessor

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
            self.xps_processor = XPSProcessor(message)
            await self.publish(message)

        elif isinstance(message, XPSRawEvent):
            if not self.xps_processor:
                logger.error(
                    "Received XPSRawEvent without an active XPSProcessor. Started after labview started?"
                )
                return
            result: XPSRawEvent = await asyncio.to_thread(
                self.xps_processor.process_frame, message
            )
            if result:
                await self.publish(result)

        elif isinstance(message, XPSStop):
            data_frame_model = DataFrameModel(df=timer.timing_dataframe)
            new_msg = XPSResultStop(function_timings=data_frame_model)
            await self.publish(new_msg)
            self.xps_processor = None
