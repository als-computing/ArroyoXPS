from dataclasses import dataclass

import numpy as np


@dataclass
class CalculatedItem:
    """Class for keeping track of all calculated items."""

    integrated_frame: np.array
    detected_peaks: np.array
    vfft: np.array
    ifft: np.array
    sum: np.array
