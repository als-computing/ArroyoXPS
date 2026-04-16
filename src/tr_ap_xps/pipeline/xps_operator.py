import asyncio
import logging
import os

import numpy as np
from arroyopy.operator import Operator
from arroyopy.schemas import Message

from ..schemas import XPSResult, XPSResultStart, XPSResultStop, XPSRawEvent, XPSStart, XPSStop, NumpyArrayModel
from ..timing import timer
from .xps_processor import XPSProcessor

def setup_logger(log_level: str = "INFO"):
    formatter = logging.Formatter("%(levelname)s: (%(name)s)  %(message)s ")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root_logger = logging.getLogger("xps_processor")
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level.upper())

setup_logger(os.getenv("LOGGING_LEVEL", "DEBUG"))

logger = logging.getLogger("xps_processor.XPSOperator")  


class XPSOperator(Operator):
    def __init__(self, build_heatmaps: bool = False) -> None:
        super().__init__()
        self.xps_processor = None
        self.build_heatmaps = build_heatmaps
        self.cumulative_sum = None
        self.total_cycles = 0

    def _compute_timepix_arrays(self, message: XPSRawEvent):
        raw_array = message.image.array.astype(np.float64)
        cycles_in_flush = message.image_info.cycles_in_flush or 1
        logger.debug(f"_compute_timepix_arrays: raw_array.shape={raw_array.shape}, cycles_in_flush={cycles_in_flush}")

        if self.cumulative_sum is None:
            self.cumulative_sum = raw_array.copy()
            self.total_cycles = cycles_in_flush
        else:
            self.cumulative_sum += raw_array
            self.total_cycles += cycles_in_flush

        integrated_2d = raw_array if raw_array.ndim == 2 else np.sum(raw_array, axis=1)
        average = self.cumulative_sum / self.total_cycles
        shot_mean_2d = average if average.ndim == 2 else np.sum(average, axis=1)
        logger.debug(f"_compute_timepix_arrays: integrated_2d.shape={integrated_2d.shape}, shot_mean_2d.shape={shot_mean_2d.shape}")

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
            logger.info(f"Start message received: scan_name={message.scan_name}")
            timer.reset()
            self.xps_processor = XPSProcessor(message)
            self.cumulative_sum = None
            self.total_cycles = 0
            await self.publish(XPSResultStart(scan_name=message.scan_name))

        elif isinstance(message, XPSRawEvent):
            logger.debug(f"XPSRawEvent received: frame_number={message.image_info.frame_number}")
            if self.build_heatmaps:
                if not self.xps_processor:
                    logger.error("Received XPSRawEvent without an active XPSProcessor. Started after labview started?")
                    return
                result: XPSResult = await asyncio.to_thread(
                    self.xps_processor.process_frame, message
                )
            else:
                try:
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
                except Exception as e:
                    logger.error(f"Error computing timepix arrays: {e}", exc_info=True)
                    return
            if result:
                logger.debug(f"Publishing XPSResult: frame_number={result.frame_number}, shot_num={result.shot_num}")
                await self.publish(result)
            else:
                logger.debug("Result is None, not publishing")

        elif isinstance(message, XPSStop):
            logger.info("Stop message received")
            self.cumulative_sum = None
            self.total_cycles = 0
            self.xps_processor = None
            try:
                await self.publish(XPSResultStop(
                    function_timings=timer.timing_dataframe
                ))
            except Exception as e:
                logger.error(f"Error publishing XPSResultStop: {e}", exc_info=True)

        else:
            logger.warning(f"Unknown message type received: {type(message)}")


def build_xps_operator(build_heatmaps: bool = False) -> XPSOperator:
    return XPSOperator(build_heatmaps=build_heatmaps)