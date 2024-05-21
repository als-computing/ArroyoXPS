from dataclasses import dataclass

import numpy as np

from .fft_calculating import calculate_fft_items
from .peak_fitting import peak_fit


@dataclass
class CalculatedItem:
    """Class for keeping track of all calculated items."""

    integrated_frame: np.array
    detected_peaks: np.array
    vfft: np.array
    ifft: np.array
    sum: np.array


def calculate(array: np.array, repeat_factor=20):
    """
    Array is of shape (frame index, x, y)
    """
    curr_frame = array[-1, :, :]
    integrated_frame = np.mean(curr_frame, axis=0)
    detected_peaks = peak_fit(integrated_frame)
    vfft, sum, ifft = calculate_fft_items(array, repeat_factor)

    result = CalculatedItem(integrated_frame, detected_peaks, vfft, sum, ifft)
    return result
