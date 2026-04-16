import asyncio
import logging

import numpy as np
from arroyopy.operator import Operator
from arroyopy.schemas import Message

from ..schemas import XPSResult, XPSResultStart, XPSResultStop, XPSRawEvent, XPSStart, XPSStop, NumpyArrayModel
from ..timing import timer
from .xps_processor import XPSProcessor

logger = logging.getLogger(__name__)


class XPSOperator(Operator):
    """
    XPSOperator is responsible for handling XPS-related messages and processing frames.

    """

    def __init__(self, build_heatmaps: bool = False) -> None:
        super().__init__()  # CHANGED: required by new arroyopy — sets up listener_queue
        self.xps_processor = None
        self.build_heatmaps = build_heatmaps
        self.cumulative_sum = None  # ADDED: for Timepix running mean
        self.total_cycles = 0       # ADDED: for Timepix running mean

    def _compute_timepix_arrays(self, message: XPSRawEvent):
        """
        Compute integrated_2d (current flush collapsed to 2D) and
        shot_mean_2d (running mean across all flushes, collapsed to 2D).
        """
        raw_array = message.image.array.astype(np.float64)
        cycles_in_flush = message.image_info.cycles_in_flush or 1

        # Accumulate sum across flushes
        if self.cumulative_sum is None:
            self.cumulative_sum = raw_array.copy()
            self.total_cycles = cycles_in_flush
        else:
            self.cumulative_sum += raw_array
            self.total_cycles += cycles_in_flush

        # Collapse 3D (x, n_bins, y) → 2D by summing axis=1
        integrated_2d = raw_array if raw_array.ndim == 2 else np.sum(raw_array, axis=1)

        # Running mean, collapsed to 2D
        average = self.cumulative_sum / self.total_cycles
        shot_mean_2d = average if average.ndim == 2 else np.sum(average, axis=1)

        return integrated_2d, shot_mean_2d

    async def process(self, message: Message) -> None:
        """
        Asynchronously handles different types of XPS messages. Handles the lifecycle of an XPSProcessor,
        which is tied to the start and end of a run.

        Args:
            message (Message): The message to be processed. It can be one of the following types:
                - XPSStart: Initializes the XPSProcessor and publishes XPSResultStart.
                - XPSRawEvent: Processes a frame using the XPSProcessor and publishes the result.
                - XPSStop: Finalizes the XPSProcessor and publishes XPSResultStop.

        Returns:
            None
        """
        if isinstance(message, XPSStart):
            timer.reset()
            self.xps_processor = XPSProcessor(message)
            self.cumulative_sum = None  # reset on new scan
            self.total_cycles = 0       # reset on new scan
            await self.publish(XPSResultStart(scan_name=message.scan_name))

        elif isinstance(message, XPSRawEvent):

            if self.build_heatmaps:
                if not self.xps_processor:
                    logger.error(
                        "Received XPSRawEvent without an active XPSProcessor. Started after labview started?"
                    )
                    return
                result: XPSResult = await asyncio.to_thread(
                    self.xps_processor.process_frame, message
                )
            else:
                integrated_2d, shot_mean_2d = self._compute_timepix_arrays(message)
                result = XPSResult(
                    shot_num=message.image_info.frame_number,
                    integrated_frames=NumpyArrayModel(array=integrated_2d),
                    frame_number=message.image_info.frame_number,
                    detected_peaks=None,
                    vfft=None,
                    ifft=None,
                    shot_recent=None,
                    shot_mean=NumpyArrayModel(array=shot_mean_2d),
                    shot_std=None,
                )
            if result:
                await self.publish(result)

        elif isinstance(message, XPSStop):
            self.cumulative_sum = None  # clean up
            self.total_cycles = 0       # clean up
            self.xps_processor = None
            await self.publish(XPSResultStop(
                function_timings=timer.timing_dataframe
            ))


# ADDED: factory function for YAML instantiation
def build_xps_operator(build_heatmaps: bool = False) -> XPSOperator:
    return XPSOperator(build_heatmaps=build_heatmaps)