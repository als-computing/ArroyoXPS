import numpy as np
import collections
import sys
sys.path.append('../')
from tr_ap_xps.peak_fitting import get_peaks
# from tr_ap_xps.calculate import calculate


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



if __name__ == "__main__":
    test_peak_detection()