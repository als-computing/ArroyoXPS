import asyncio
import logging

from arroyo.operator import AbstractOperator
from arroyo.publisher import AbstractPublisher
from arroyo.schemas import Message
from tiled.client import node

from .processor import XPSProcessor
from .schemas import XPSRawEvent, XPSStart, XPSStop

logger = logging.getLogger("tr-ap-xps.writer")


class XPSOperator(AbstractOperator):
    """
    XPSOperator is responsible for handling XPS-related messages and processing frames.
    Attributes:
        publisher (AbstractPublisher): The publisher used to publish messages.
        tiled_runs_node (node): The node containing tiled runs data.
        xps_processor (XPSProcessor, optional): The processor used to handle XPS frames.
    Methods:
        __init__(publisher: AbstractPublisher, tiled_runs_node: node) -> None:
            Initializes the XPSOperator with a publisher and a tiled runs node.
        run(message: Message) -> None:
            Asynchronously handles incoming messages. Depending on the message type,
            it either starts the XPS processing, processes a frame, or stops the XPS processing.
    """

    def __init__(self, publisher: AbstractPublisher, tiled_runs_node: node) -> None:
        self.tiled_runs_node = tiled_runs_node
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
            await self.publish(message)
            self.xps_processor = XPSProcessor(self.tiled_runs_node, message)
        elif isinstance(message, XPSRawEvent):
            if not self.xps_processor:
                return
            result: XPSRawEvent = await asyncio.to_thread(
                self.xps_processor.process_frame, message
            )
            if result:
                await self.publish(XPSRawEvent)
        elif isinstance(message, XPSStop):
            await self.publish(message)
            if self.xps_processor:
                self.xps_processor.finish(message)
            self.xps_processor = None
