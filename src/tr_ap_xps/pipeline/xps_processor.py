import logging

import numpy as np

from ..schemas import DataFrameModel, NumpyArrayModel, XPSRawEvent, XPSResult, XPSStart
from ..timing import timer
from .fft import calculate_fft_items
from .peak_fitting import peak_fit

logger = logging.getLogger("tr_ap_xps.processor")


class XPSProcessor:
    """
    A class to process XPS (X-ray Photoelectron Spectroscopy) data.

    """

    def __init__(self, message: XPSStart):
        self.frames_per_cycle = message.f_reset
        self.integrated_frames: np.ndarray = None
        self.shot_num = 0
        self.shot_sum: np.ndarray = None

    @timer
    def _compute_mean(self, curr_frame: np.array):
        return np.mean(curr_frame, axis=0)

    @timer
    def process_frame(self, message: XPSRawEvent) -> None:
        # Compute horizontally-integrated frame
        new_integrated_frame = self._compute_mean(message.image.array)

        # Update the local cached dataframes
        if self.integrated_frames is None:
            self.integrated_frames = new_integrated_frame[None, :]
        else:
            # self.integrated_frames = np.vstack(
            #     (self.integrated_frames, new_integrated_frame)
            # )
            self.integrated_frames = np.vstack(
                (new_integrated_frame, self.integrated_frames)
            )

        # Things to do with every shot (a "shot" is a complete cycle of frames)
        if message.image_info.frame_number % self.frames_per_cycle == 0:
            self.shot_num += 1
            if self.shot_sum is None:
                self.shot_sum = self.integrated_frames
            else:
                self.shot_sum = self.shot_sum + self.integrated_frames

            
            logger.info(f"Processing frame {message.image_info.frame_number}")
            # Peak detection on new_integrated_frame
            detected_peaks_df = peak_fit(new_integrated_frame)
            # TODO: allow user to select repeat factor and width on UI
            vfft_np, ifft_np = calculate_fft_items(
                self.integrated_frames, repeat_factor=20, width=0
            )

            result = XPSResult(
                frame_number=message.image_info.frame_number,
                integrated_frames=NumpyArrayModel(array=self.integrated_frames),
                detected_peaks=DataFrameModel(df=detected_peaks_df),
                vfft=NumpyArrayModel(array=vfft_np),
                ifft=NumpyArrayModel(array=ifft_np),
                shot_num=self.shot_num,
                shot_sum=NumpyArrayModel(array=self.shot_sum),
            )
            return result

        timer.end_frame()
