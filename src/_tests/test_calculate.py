from pathlib import Path

import numpy as np
import pytest

from tr_ap_xps.calculate import calculate
from tr_ap_xps.fft_calculating import calculate_fft_items
from tr_ap_xps.peak_fitting import get_peaks


@pytest.fixture
def test_array(file_name="./src/_tests/test_array_300_1131.npy"):
    """
    Helper function to load the test array, each row of the test array is a integrated frame already
    """
    file_path = Path(file_name)
    array = np.load(file_path)
    return array


@pytest.fixture
def test_raw_array(file_name="./src/_tests/test_raw_frame_269_1131.npy"):
    """
    Helper function to load the one test raw frame
    """
    file_path = Path(file_name)
    array = np.load(file_path)
    # we need to simulate the raw incoming array, which is of shape (frame index, x, y)
    # let's simulate 100 incoming raw arrays
    duplicated_array = np.stack([array] * 100)
    return duplicated_array


def test_peak_detection(test_array):
    """Test the peak detection functionality."""
    x = np.arange(test_array.shape[1])
    y = test_array[-1, :]

    return_list, unfit_list, fit_list, residual, base_list = get_peaks(x, y, 2, "g")
    peak_locations = [peak["index"] for peak in return_list]

    assert len(peak_locations) == 2, f"Expected 2 peaks, found {len(peak_locations)}"
    assert peak_locations[0] in range(
        300, 400
    ), f"First peak at unexpected location {peak_locations[0]}"
    assert peak_locations[1] in range(
        600, 700
    ), f"Second peak at unexpected location {peak_locations[1]}"


def test_fft_items(test_array):
    """Test the FFT calculation functionality."""
    vfft, sum, ifft = calculate_fft_items(test_array)

    assert vfft.shape == test_array.shape, "vfft shape mismatch"
    assert len(sum.shape) == 1, "sum should be a 1D array"
    assert ifft.shape == test_array.shape, "ifft shape mismatch"


def test_calculate(test_raw_array):
    """Test the main calculate function."""
    calculated_item = calculate(test_raw_array, repeat_factor=20)

    assert (
        len(calculated_item.integrated_frame.shape) == 1
    ), "integrated_frame should be 1D"
    assert isinstance(
        calculated_item.detected_peaks, np.ndarray
    ), "detected_peaks should be an ndarray"
    assert isinstance(calculated_item.vfft, np.ndarray), "vfft should be an ndarray"
    assert isinstance(calculated_item.sum, np.ndarray), "sum should be an ndarray"
    assert isinstance(calculated_item.ifft, np.ndarray), "ifft should be an ndarray"
