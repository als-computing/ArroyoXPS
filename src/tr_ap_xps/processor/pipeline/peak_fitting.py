"""
This is a script for peak fitting.
This code is modify from https://github.com/mlexchange/mlex_peak_detection.
Specifically, the part related with base_line and block were removed.
"""

import collections
import warnings

import numpy as np
import pandas as pd
from astropy.modeling import fitting, models
from scipy import signal

warnings.filterwarnings(
    "ignore",
    message="The fit may be unsuccessful; Maximum number of iterations reached.",
    category=UserWarning,
    module="astropy.modeling.optimizers",
)


# find the bins
def bayesian_block_finder(
    x: np.ndarray = np.ones(
        5,
    ),
    y: np.ndarray = np.ones(
        5,
    ),
):
    """bayesian_block_finder performs Bayesian Block analysis on x, y data.
    see Jeffrey Scargle's papers at doi: 10.1088/0004-637X/764/2/167
    :param x: array of x-coordinates
    :type x: numpy.ndarray
    :param y: array of y-values with same length as x
    :type y: numpy.ndarray
    """
    numPts = len(x)
    if len(x) != len(y):
        raise ValueError("x and y are not of equal length")

    sigmaGuess = np.std(y[y <= np.median(y)])
    cellData = sigmaGuess * np.ones(len(x))

    ncp_prior = 0.5

    cp = []

    iterCnt = 0
    iterMax = 10

    while iterCnt <= iterMax:
        best = []
        last = []

        for r in range(numPts):
            # y-data background subtracted
            sumX1 = np.cumsum(y[r::-1])
            sumX0 = np.cumsum(cellData[r::-1])  # sigma guess
            fitVec = np.power(sumX1[r::-1], 2) / (4 * sumX0[r::-1])

            paddedBest = np.insert(best, 0, 0)
            best.append(np.amax(paddedBest + fitVec - ncp_prior))
            last.append(np.argmax(paddedBest + fitVec - ncp_prior))

            # print('Best = {0},  Last = {1}'.format(best[r], last[r]))

        # Find change points by peeling off last block iteratively
        index = last[numPts - 1]

        while index > 0:
            cp = np.concatenate(([index], cp))
            index = last[index - 1]

        # Iterate if desired, to implement later
        iterCnt += 1
        break

    numCP = len(cp)
    numBlocks = numCP + 1

    rateVec = np.zeros(numBlocks)

    cptUse = np.insert(cp, 0, 0)

    print("numBlocks: {0}, dataPts/Block: {1}".format(numBlocks, len(x) / numBlocks))
    for idBlock in range(numBlocks):
        # set ii1, ii2 as indexes.  Fix edge case at end of blocks
        ii1 = int(cptUse[idBlock])
        if idBlock < (numBlocks - 1):
            ii2 = int(cptUse[idBlock + 1] - 1)
        else:
            ii2 = int(numPts)

        subset = y[ii1:ii2]
        weight = cellData[ii1:ii2]
        if ii1 == ii2:
            subset = y[ii1]
            weight = cellData[ii1]
        rateVec[idBlock] = np.dot(weight, subset) / np.sum(weight)

        if np.sum(weight) == 0:
            raise ValueError("error, divide by zero at index: {0}".format(idBlock))
            print("-------ii1: {0}, ii2: {1}".format(ii1, ii2))

    # Simple hill climbing for merging blocks
    cpUse = np.concatenate(([1], cp, [len(y)]))
    cp = cpUse

    numCP = len(cpUse) - 1
    idLeftVec = np.zeros(numCP)
    idRightVec = np.zeros(numCP)

    for i in range(numCP):
        idLeftVec[i] = cpUse[i]
        idRightVec[i] = cpUse[i + 1]

    # Find maxima defining watersheds, scan for
    # highest neighbor of each block

    idMax = np.zeros(numBlocks)
    idMax = np.zeros(numBlocks)
    for j in range(numBlocks):
        jL = (j - 1) * (j > 0) + 0 * (j <= 0)  # prevent out of bounds
        jR = (j + 1) * (j < (numBlocks - 1)) + (numBlocks - 1) * (j >= (numBlocks - 1))

        rateL = rateVec[jL]
        rateC = rateVec[j]
        rateR = rateVec[jR]
        rateList = [rateL, rateC, rateR]

        jMax = np.argmax(rateList)  # get direction [0, 1, 2]
        idMax[j] = j + jMax - 1  # convert direction to delta

    idMax[idMax > numBlocks] = numBlocks
    idMax[idMax < 0] = 0

    # Implement hill climbing (HOP algorithm)

    hopIndex = np.array(range(numBlocks))  # init: all blocks point to self
    hopIndex = hopIndex.astype(int)  # cast all as int
    ctr = 0
    # point each block to its max block
    while ctr <= len(x):
        newIndex = idMax[hopIndex]  # Point each to highest neighbor

        if np.array_equal(newIndex, hopIndex):
            break
        else:
            hopIndex = newIndex.astype(int)

        ctr += 1
        if ctr == len(x):
            print("Hill climbing did not converge...?")

    idMax = np.unique(hopIndex)
    numMax = len(idMax)

    # Convert to simple list of block boundaries
    boundaries = [0]
    for k in range(numMax):
        currVec = np.where(hopIndex == idMax[k])[0]

        rightDatum = idRightVec[currVec[-1]] - 1  # stupid leftover matlab index
        boundaries.append(rightDatum)

    return np.array(boundaries)


def peak_helper(x_data, y_data, num_peaks, peak_shape):
    x_data = np.array(x_data)
    y_data = np.array(y_data)
    c = 2 * np.sqrt(2 * np.log(2))
    ind_peaks = signal.find_peaks_cwt(y_data, 100)
    ref = signal.cwt(y_data, signal.ricker, list(range(1, 10)))
    ref = np.clip(ref, a_min=1e-10, a_max=None)
    ref = np.log(ref + 1)
    if len(ind_peaks) == 0:
        return [], [], [], None, None
    init_xpeaks = x_data[ind_peaks]
    init_ypeaks = y_data[ind_peaks]
    sorted_ind_peaks = init_ypeaks.argsort()
    sorted_ind_peaks = ind_peaks[sorted_ind_peaks]
    if len(sorted_ind_peaks) > num_peaks:
        init_xpeaks = x_data[sorted_ind_peaks[-num_peaks:]]
        init_ypeaks = y_data[sorted_ind_peaks[-num_peaks:]]
        ind_peaks = sorted_ind_peaks[-num_peaks:]
    g_unfit = None
    for ind, (xpeak, ypeak) in enumerate(
        zip(np.flip(init_xpeaks), np.flip(init_ypeaks))
    ):
        i = ind_peaks[ind]
        largest_width = 0
        for i_img in range(len(ref)):
            if ref[i_img][i] > largest_width:
                largest_width = ref[i_img][i]
        sigma = (largest_width * (x_data[1] - x_data[0])) / c
        if peak_shape == "Voigt":
            g_init = models.Voigt1D(
                x_0=xpeak,
                amplitude_L=ypeak,
                fwhm_L=c * sigma,  # 2*gamma,
                fwhm_G=c * sigma,
            )
        else:
            g_init = models.Gaussian1D(amplitude=ypeak, mean=xpeak, stddev=sigma)
        if g_unfit is None:
            g_unfit = g_init
        else:
            g_unfit = g_unfit + g_init
    fit_g = fitting.SimplexLSQFitter()
    if init_xpeaks.shape[0] == 1:
        fit_g = fitting.LevMarLSQFitter()
    g_fit = fit_g(g_unfit, x_data, y_data)
    residual = np.abs(g_fit(x_data) - y_data)
    epsilon = 1e-5
    y_data = y_data + epsilon
    if np.mean(residual / y_data) > 0.10:
        flag_list = list(np.ones(num_peaks))
    else:
        flag_list = list(np.zeros(num_peaks))
    FWHM_list = []
    amplitude_list = []

    if len(init_ypeaks) == 1:
        if peak_shape == "Voigt":
            FWHM_list.append(g_fit.fwhm_G.value)
            amplitude_list.append(g_fit.amplitude_L.value)
        else:
            FWHM_list.append(g_fit.stddev.value)
            amplitude_list.append(g_fit.amplitude.value)
    else:
        for i in range(len(init_ypeaks)):
            if peak_shape == "Voigt":
                FWHM_list.append(1 * getattr(g_fit, f"fwhm_G_{i}"))
                amplitude_list.append(
                    getattr(g_fit, f"amplitude_{len(init_ypeaks) - i - 1}").value
                )
            else:
                FWHM_list.append(
                    c * getattr(g_fit, f"stddev_{len(init_ypeaks) - i - 1}") * 100
                )
                amplitude_list.append(
                    getattr(g_fit, f"amplitude_{len(init_ypeaks) - i - 1}").value
                )
    return ind_peaks, FWHM_list, flag_list, g_unfit, g_fit, amplitude_list


def get_peaks(x_data, y_data, num_peaks, peak_shape):
    base_list = None
    unfit_list = [[], []]
    fit_list = [[], []]
    residual = [[], []]
    g_unfit = None
    g_fit = None

    FWHM_list = []
    peak_list = []
    flag_list = []
    amplitude_list = []

    peak_list, FWHM_list, flag_list, g_unfit, g_fit, amplitude_list = peak_helper(
        x_data, y_data, num_peaks, peak_shape
    )
    unfit_list[0].extend(x_data)
    fit_list[0].extend(x_data)
    for i in x_data:
        if g_unfit is not None:
            unfit_list[1].append(g_unfit(i))
            fit_list[1].append(g_fit(i))
        else:
            unfit_list[1].append(0)
            fit_list[1].append(0)

    return_list = []
    for i in range(len(peak_list)):
        diction = {}
        diction["index"] = peak_list[i]
        diction["FWHM"] = FWHM_list[i]
        diction["flag"] = flag_list[i]
        diction["amplitude"] = amplitude_list[i]
        return_list.append(diction)

    residual[0].extend(fit_list[0])
    temp_fit = np.array(fit_list[1])
    temp_y = np.array(y_data)
    resid = temp_y - temp_fit
    residual[1].extend(resid)

    return return_list, unfit_list, fit_list, residual, base_list


def peak_fit(one_d_array: np.ndarray):
    assert one_d_array.ndim == 1, "Input array must be 1-dimensional"
    x = np.arange(one_d_array.shape[0])
    return_list, unfit_list, fit_list, residual, base_list = get_peaks(
        x, one_d_array, 2, "g"
    )
    # return table (location, amplitude, FWHM)
    result = collections.defaultdict(list)
    for peak in return_list:
        result["index"].append(peak["index"])
        result["amplitude"].append(peak["amplitude"])
        result["FWHM"].append(peak["FWHM"])
    return pd.DataFrame(result)
