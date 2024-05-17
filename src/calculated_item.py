from dataclasses import dataclass
import numpy as np

from peak_fitting import peak_fit

@dataclass
class CalculatedItem:
    """Class for keeping track of all calculated items."""
    integrated_frame: np.array
    detected_peaks: np.array
    vfft: np.array
    ifft: np.array
    sum: np.array

    def __init__(self, 
                 integrated_frame: np.array, 
                 detected_peaks: np.array,
                 vfft: np.array,
                 ifft: np.array,
                 sum: np.array):
        self.integrated_frame = integrated_frame #avg = np.mean(raw_frame, axis=0)
        self.detected_peaks = detected_peaks, #peak_fit(self.integrated_frame)
        self.vfft = vfft
        self.ifft = ifft
        self.sum = sum