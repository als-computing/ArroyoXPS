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
        self.shot_cache = (
            None  # built up with each integrated frame, reset at the end of each shot
        )
        self.recent_shot = None  # updated at the completion of each shot
        self.shot_rolling_mean = None
        self.shot_rolling_variance = None
        self.shot_rolling_std = None

    @timer
    def _compute_mean(self, curr_frame: np.array):
        return np.mean(curr_frame, axis=0)

    @timer
    def _compute_rolling_values(self, curr_frame: np.array):
        if self.shot_rolling_mean is None:
            self.shot_rolling_mean = curr_frame
            self.shot_rolling_std = np.zeros_like(curr_frame)
            self.shot_rolling_variance = self.shot_rolling_std
        else:
            new_mean = self.shot_rolling_mean + (curr_frame - self.shot_rolling_mean) / self.shot_num
            self.shot_rolling_variance += (curr_frame - self.shot_rolling_mean) * (curr_frame - new_mean)
            self.shot_rolling_mean = new_mean
            self.shot_rolling_std = np.sqrt(self.shot_rolling_variance / self.shot_num)

    @timer
    def process_frame(self, message: XPSRawEvent) -> None:
        try:
            # Compute horizontally-integrated frame
            new_integrated_frame = self._compute_mean(message.image.array)

            # Update the local cached arrays
            if self.integrated_frames is None:
                self.integrated_frames = new_integrated_frame[None, :]
            else:
                # self.integrated_frames = np.vstack(
                #     (self.integrated_frames, new_integrated_frame)
                # )
                self.integrated_frames = np.vstack(
                    (new_integrated_frame, self.integrated_frames)
                )

            if self.shot_cache is None:
                self.shot_cache = new_integrated_frame[
                    np.newaxis, :
                ]  # add a new axis frame number
            else:
                self.shot_cache = np.vstack((self.shot_cache, new_integrated_frame))

            # Things to do with every shot (a "shot" is a complete cycle of frames)
            if (
                message.image_info.frame_number != 0
                and message.image_info.frame_number % self.frames_per_cycle == 0
            ):
                self.shot_num += 1
                if self.recent_shot is None:
                    self.recent_shot = self.shot_cache
  
                else:
                    self.recent_shot = self.recent_shot + self.shot_cache
                self._compute_rolling_values(self.shot_cache)


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
                    shot_recent=NumpyArrayModel(array=self.recent_shot),
                    shot_mean=NumpyArrayModel(array=self.shot_rolling_mean),
                    shot_std=NumpyArrayModel(array=self.shot_rolling_std),
                )
                self.shot_cache = None
                return result 
        except Exception as e:
            logger.exception(f"Error processing frame: {e}")
            return None
        timer.end_frame()
