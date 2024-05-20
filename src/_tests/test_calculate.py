import numpy as np
import collections
import matplotlib.pyplot as plt
from peak_fitting import get_peaks

def test():
    """
    This function will plot the peak locations for the entire data
    """
    file_path = "/Users/runbojiang/Desktop/AP-XPS-my/avg_array_3.npy"
    array = np.load(file_path)
    print(array.shape)
    x = np.arange(array.shape[1])
    peak_locations = collections.defaultdict(list)
    # for i in range(array.shape[0]):
    for i in range(300):
        y = array[i, :]
        return_list, unfit_list, fit_list, residual, base_list = get_peaks(x, y, 2, 'g')
        for peak in return_list:
            peak_locations[i].append(peak['index'])

    # plot the location of first and second peak
    for key in peak_locations:
        peak_locations[key].sort()
    keys = list(peak_locations.keys())
    first_peak_locations = [peak_locations[key][0] for key in keys]
    second_peak_locations = [peak_locations[key][1] for key in keys]
    plt.figure(figsize=(10, 5))
    plt.plot(keys, first_peak_locations, label='First Peak Mean', marker='o')
    plt.plot(keys, second_peak_locations , label='Second Peak Mean', marker='o')
    plt.grid(True)
    # Show plot
    plt.show()