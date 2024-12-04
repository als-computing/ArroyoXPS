import numpy as np

from ..timing import timer


@timer
def get_vfft(array: np.array):
    """
    Perform fft along colmns
    """
    epsilon = 1e-5
    return np.abs(np.log(np.abs(np.fft.fft(array[:, :], axis=0)) + epsilon))


@timer
def get_sum(array: np.array):
    return np.sum(array[:, :], axis=1)


@timer
def get_ifft(array: np.array, repeat_factor: int = 25, width: int = 0):
    """
    Perform IFFT filtering on the input array.
    Parameters:
    array (np.array): Input array to filter.
    repeat_factor (int): Repeat factor for the input array.
    width (int): Width for the filter (default is 0).
    Returns:
    np.array: Filtered array after inverse FFT.
    """
    # Perform FFT along the columns
    fcarray = np.fft.fft(array, axis=0)
    # Initialize a zero array of the same shape and dtype complex
    array2 = np.zeros(fcarray.shape, dtype=complex)
    # Calculate the step size for sampling
    dummy = int(fcarray.shape[0] / repeat_factor)
    # Sample every 'dummy'-th row and also copy 'width' rows before and after each sampled index

    # TODO what do do if dummy rounds down to zero?
    if dummy == 0:
        dummy = 1
    for i in range(0, fcarray.shape[0], dummy):
        start = max(0, i - width)
        end = min(fcarray.shape[0], i + width + 1)
        array2[start:end] = fcarray[start:end]

    # Perform inverse FFT
    ifcarray = np.fft.ifft(array2, axis=0)

    return np.abs(ifcarray)


@timer
def calculate_fft_items(array: np.array, repeat_factor: int = 20, width: int = 0):
    assert (
        isinstance(repeat_factor, int) and repeat_factor > 0
    ), "Repeat factor is a positive integer."

    array = np.array(array)
    vfft = get_vfft(array)
    sum = get_sum(vfft)
    ifft = get_ifft(array, repeat_factor, width)

    return vfft, sum, ifft
