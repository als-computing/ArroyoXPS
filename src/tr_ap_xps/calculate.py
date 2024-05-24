from dataclasses import dataclass

import numpy as np
import pandas as pd

# from .fft import calculate_fft_items
# from .peak_fitting import peak_fit
from fft import calculate_fft_items
from peak_fitting import peak_fit


@dataclass
class CalculatedItem:
    """Class for keeping track of all calculated items."""

    integrated_frame: np.array
    detected_peaks: pd.DataFrame
    vfft: np.array
    ifft: np.array
    sum: np.array


def integrate_frame(array: np.array):
    """
    This function integrate the input 2d raw frame into 1d.
    """

    integrated_frame = np.mean(array, axis=0)
    detected_peaks = peak_fit(integrated_frame)

    return integrated_frame, detected_peaks


def calculate(raw_frame: np.array, stacked_integrated_frames: np.array, repeat_factor=20):
    assert raw_frame.ndim == 2, "The current raw_frame is not 2D."
    assert stacked_integrated_frames.ndim == 2, "The stacked_integrated_frames array is not 2D."

    integrated_frame, detected_peaks = integrate_frame(raw_frame)
    vfft, sum, ifft = calculate_fft_items(stacked_integrated_frames, repeat_factor=repeat_factor)

    result = CalculatedItem(integrated_frame, detected_peaks, vfft, sum, ifft)
    return result
