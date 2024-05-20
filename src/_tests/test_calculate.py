import numpy as np
import sys
sys.path.append('../')
from tr_ap_xps.peak_fitting import get_peaks
from tr_ap_xps.fft_calculating import calculate_fft_items
from tr_ap_xps.calculate import calculate


def test_peak_detection():
    file_path = "test_array_300_1131.npy"
    array = np.load(file_path)
    assert array.shape[0] == 300

    x = np.arange(array.shape[1])
    y = array[-1, :]
    return_list, unfit_list, fit_list, residual, base_list = get_peaks(x, y, 2, 'g')
    peak_locations = [peak['index'] for peak in return_list]
    assert len(peak_locations) == 2
    assert peak_locations[0] in range(300, 400) and peak_locations[1] in range(600, 700)

def test_fft_items():
    file_path = "test_array_300_1131.npy"
    array = np.load(file_path)
    vfft, sum, ifft = calculate_fft_items(array)
    assert vfft.shape == array.shape
    assert len(sum.shape) == 1
    assert ifft.shape == array.shape

def test_calculate():
    file_path = "test_array_300_1131.npy"
    array = np.load(file_path)
    calculated_item = calculate(array, repeat_factor = 20)
    assert len(calculated_item.integrated_frame.shape) == 1
    assert isinstance(calculated_item.detected_peaks, np.ndarray)
    assert isinstance(calculated_item.vfft, np.ndarray)
    assert isinstance(calculated_item.sum, np.ndarray)
    assert isinstance(calculated_item.ifft, np.ndarray)


if __name__ == "__main__":
    test_peak_detection()
    test_fft_items()
    test_calculate()