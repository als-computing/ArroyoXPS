import logging

import numpy as np
import pandas as pd

from ..schemas import DataFrameModel, NumpyArrayModel, XPSRawEvent, XPSResult, XPSStart
from ..timing import timer
from .fft import calculate_fft_items
from .peak_fitting import peak_fit


logger = logging.getLogger("tr-ap-xps.processor")


class XPSProcessor:
    """
    A class to process XPS (X-ray Photoelectron Spectroscopy) data.

    """

    def __init__(self, message: XPSStart):
        self.frames_per_cycle = message.frames_per_cycle
        self.integrated_frames: np.ndarray = None
        # self.detected_peaks: pd.DataFrame = None
        # self.vfft: pd.DataFrame = None
        # self.ifft: pd.DataFrame = None
        # self.sum: pd.DataFrame = None

    @timer
    def _compute_mean(self, curr_frame: np.array):
        return np.mean(curr_frame, axis=0)

    # TODO: we do not have filtered, but 4 the other instead. So, update this part?
    # @timer
    # def _tiled_update_lines_filtered(self, new_integrated_df: pd.DataFrame):
    #     if "lines_filtered" not in self.tiled_nodes.run_node:
    #         self.tiled_nodes.lines_filtered_node = self.create_tiled_table_node(
    #             self.tiled_nodes.run_node, new_integrated_df, "lines_filtered"
    #         )
    #     else:
            # self.tiled_nodes.lines_filtered_node.append_partition(new_integrated_df, 0)

    @timer
    def process_frame(self, message: XPSRawEvent) -> None:
        # Compute horizontally-integrated frame
        new_integrated_frame = self._compute_mean(message.image.array)

        # Update the local cached dataframes
        if self.integrated_frames is None:
            self.integrated_frames = new_integrated_frame[None, :]
        else:
            self.integrated_frames = np.vstack(
                (self.integrated_frames, new_integrated_frame)
            )

        # Things to do every so often
        if message.image_info.frame_number % self.frames_per_cycle == 0:
            # Peak detection on new_integrated_frame
            detected_peaks_df = peak_fit(new_integrated_frame)
            # TODO: allow user to select repeat factor and width on UI
            vfft_np, sum_np, ifft_np = calculate_fft_items(
                self.integrated_frames, repeat_factor=20, width=0
            )

            result = XPSResult(
                frame_number=message.image_info.frame_number,
                integrated_frames=NumpyArrayModel(array=self.integrated_frames),
                detected_peaks=DataFrameModel(df=detected_peaks_df),
                vfft=NumpyArrayModel(array=vfft_np),
                ifft=NumpyArrayModel(array=ifft_np),
                sum=NumpyArrayModel(array=sum_np),
            )
            return result

        timer.end_frame()
