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
                 sum: np.array,
                 ifft: np.array,
                 ):
        self.integrated_frame = integrated_frame
        self.detected_peaks = detected_peaks
        self.vfft = vfft
        self.sum = sum
        self.ifft = ifft