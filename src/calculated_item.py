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

    def __init__(self, raw_frame: np.array):
        self.integrated_frame = avg = np.mean(raw_frame, axis=0)
        self.detected_peaks = peak_fit(self.integrated_frame)
        vfft = None
        ifft = None
        sum = None

    

    def total_cost(self) -> float:
        return self.unit_price * self.quantity_on_hand