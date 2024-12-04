from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tr_ap_xps.pipeline.fft import calculate_fft_items
from tr_ap_xps.pipeline.peak_fitting import get_peaks, peak_fit


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


def test_peak_fit(test_array):
    df = peak_fit(test_array[-1, :])
    assert isinstance(
        df, pd.DataFrame
    ), "The peak_fit return a table of (index, amplitude, FWHM)"
    assert "index" in df.columns, "index not in table column"
    assert "amplitude" in df.columns, "amplitude not in table column"
    assert "FWHM" in df.columns, "FWHM not in table column"


def test_fft_items(test_array):
    """Test the FFT calculation functionality."""
    vfft, sum, ifft = calculate_fft_items(test_array)

    assert vfft.shape == test_array.shape, "vfft shape mismatch"
    assert len(sum.shape) == 1, "sum should be a 1D array"
    assert ifft.shape == test_array.shape, "ifft shape mismatch"
