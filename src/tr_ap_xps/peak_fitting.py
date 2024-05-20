
import numpy as np
import pandas as pd
from scipy import signal
from astropy.modeling import models, fitting
import matplotlib.pyplot as plt
import collections
import time

# find the bins
def bayesian_block_finder(x: np.ndarray=np.ones(5,), y: np.ndarray=np.ones(5,),):
    """bayesian_block_finder performs Bayesian Block analysis on x, y data.
    see Jeffrey Scargle's papers at doi: 10.1088/0004-637X/764/2/167
    :param x: array of x-coordinates
    :type x: numpy.ndarray
    :param y: array of y-values with same length as x
    :type y: numpy.ndarray
    """
    data_mode = 3
    numPts = len(x)
    if len(x) != len(y):
        raise ValueError('x and y are not of equal length')

    tt = np.arange(numPts)
    nnVec = []

    sigmaGuess = np.std(y[ y <= np.median(y)])
    cellData = sigmaGuess * np.ones(len(x))

    ncp_prior = 0.5


    ## To implement: trimming/choosing of where to start/stop
    ## To implement: timing functions

    cp = []
    cntVec = []

    iterCnt = 0
    iterMax = 10

    while iterCnt <= iterMax:
        best = []
        last = []

        for r in range(numPts):
            # y-data background subtracted
            sumX1 = np.cumsum(y[r::-1]) 
            sumX0 = np.cumsum(cellData[r::-1]) # sigma guess
            fitVec = (np.power(sumX1[r::-1],2) / (4 * sumX0[r::-1]))

            paddedBest = np.insert(best,0,0)
            best.append(np.amax( paddedBest + fitVec - ncp_prior ))
            last.append(np.argmax( paddedBest + fitVec - ncp_prior ) )

            # print('Best = {0},  Last = {1}'.format(best[r], last[r]))

        # Find change points by peeling off last block iteratively
        index = last[numPts-1]

        while index > 0:
            cp = np.concatenate( ([index], cp) )
            index = last[index-1]

        # Iterate if desired, to implement later
        iterCnt += 1
        break


    numCP = len(cp)
    numBlocks = numCP + 1

    rateVec  = np.zeros(numBlocks)
    numVec   = np.zeros(numBlocks)

    cptUse = np.insert(cp, 0, 0)

    #print('cptUse start: {0}, end: {1}, len: {2}'.format(cptUse[0],
                                                    #cptUse[-1], len(cptUse)))
    #print('lenCP: {0}'.format(len(cp)))
    
    # what does this stuff do I don't know... ( good one man )
    print('numBlocks: {0}, dataPts/Block: {1}'.format(numBlocks, len(x)/numBlocks))
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
            raise ValueError('error, divide by zero at index: {0}'.format(idBlock))
            print('-------ii1: {0}, ii2: {1}'.format(ii1, ii2))

    # Simple hill climbing for merging blocks
    cpUse = np.concatenate(([1], cp, [len(y)]))
    cp = cpUse

    numCP = len(cpUse) - 1
    idLeftVec = np.zeros(numCP)
    idRightVec = np.zeros(numCP)

    for i in range(numCP):
        idLeftVec[i] = cpUse[i]
        idRightVec[i] = cpUse[i+1]

    # Find maxima defining watersheds, scan for 
    # highest neighbor of each block

    idMax = np.zeros(numBlocks)
    idMax = np.zeros(numBlocks)
    for j in range(numBlocks):
        jL = (j-1)*(j>0) + 0*(j<=0) # prevent out of bounds
        jR = (j+1)*(j<(numBlocks-1)) + (numBlocks-1)*(j>=(numBlocks-1))

        rateL = rateVec[jL]
        rateC = rateVec[j]
        rateR = rateVec[jR]
        rateList = [rateL, rateC, rateR]

        jMax = np.argmax(rateList) #get direction [0, 1, 2]
        idMax[j] = j + jMax - 1 # convert direction to delta

    idMax[ idMax > numBlocks] = numBlocks
    idMax[ idMax < 0] = 0

    # Implement hill climbing (HOP algorithm)
    
    hopIndex = np.array(range(numBlocks)) # init: all blocks point to self
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
            print('Hill climbing did not converge...?')

    idMax = np.unique(hopIndex)
    numMax = len(idMax)

    # Convert to simple list of block boundaries
    boundaries = [0]
    for k in range(numMax):
        currVec = np.where(hopIndex == idMax[k])[0]

        rightDatum = idRightVec[currVec[-1]] - 1 # stupid leftover matlab index
        boundaries.append(rightDatum)
    
    return np.array(boundaries)


def peak_helper(x_data, y_data, num_peaks, peak_shape):
    x_data = np.array(x_data)
    y_data = np.array(y_data)
    c = 2*np.sqrt(2*np.log(2))
    ind_peaks = signal.find_peaks_cwt(y_data, 100)
    ref = signal.cwt(y_data, signal.ricker, list(range(1, 10)))
    ref = np.log(ref+1)
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
    for ind, (xpeak, ypeak) in enumerate(zip(np.flip(init_xpeaks), np.flip(init_ypeaks))):
        i = ind_peaks[ind]
        largest_width = 0
        for i_img in range(len(ref)):
            if ref[i_img][i] > largest_width:
                largest_width = ref[i_img][i]
        sigma = (largest_width * (x_data[1]-x_data[0])) / c
        if peak_shape == 'Voigt':
            g_init = models.Voigt1D(x_0=xpeak,
                                    amplitude_L=ypeak,
                                    fwhm_L=c*sigma, #2*gamma,
                                    fwhm_G=c*sigma)
        else:
            g_init = models.Gaussian1D(amplitude=ypeak,
                                       mean=xpeak,
                                       stddev=sigma)
        if g_unfit is None:
            g_unfit = g_init
        else:
            g_unfit = g_unfit + g_init
    fit_g = fitting.SimplexLSQFitter()
    if init_xpeaks.shape[0] == 1:
        fit_g = fitting.LevMarLSQFitter()
    g_fit = fit_g(g_unfit, x_data, y_data)
    residual = np.abs(g_fit(x_data) - y_data)
    if np.mean(residual/y_data) > 0.10:
        flag_list = list(np.ones(num_peaks))
    else:
        flag_list = list(np.zeros(num_peaks))
    FWHM_list = []
    if len(init_ypeaks) == 1:
        if peak_shape == 'Voigt':
            FWHM_list.append(g_fit.fwhm_G.value)
        else:
            FWHM_list.append(g_fit.stddev.value)
    else:
        for i in range(len(init_ypeaks)):
            if peak_shape == 'Voigt':
                FWHM_list.append(1*getattr(g_fit, f"fwhm_G_{i}"))
            else:
                FWHM_list.append(c*getattr(g_fit, f"stddev_{i}"))
    return ind_peaks, FWHM_list, flag_list, g_unfit, g_fit

def get_peaks(x_data, y_data, num_peaks, peak_shape, baseline=None, block=None):
    base_list = None
    unfit_list = [[], []]
    fit_list = [[], []]
    residual = [[], []]
    base_model = None
    g_unfit = None
    g_fit = None
    # Linear Model from data on the left wall of the window to data on the
    # right wall of the window
    if baseline:
        base_list = [[], []]
        slope = (y_data[-1] - y_data[0])/(x_data[-1] - x_data[0])
        intercept = y_data[0] - (slope * x_data[0])
        base_model = models.Linear1D(slope=slope, intercept=intercept)
        base = list(base_model(np.array(x_data)))
        y_data = list(np.array(y_data) - base_model(np.array(x_data)))
        base_list[0] = x_data
        base_list[1] = base

    FWHM_list = []
    peak_list = []
    flag_list = []

    if block:
        boundaries = bayesian_block_finder(np.array(x_data), np.array(y_data))
        for bound_i in range(len(boundaries)):
            lower = int(boundaries[bound_i])
            if bound_i == (len(boundaries)-1):
                upper = len(x_data)
            else:
                upper = int(boundaries[bound_i+1])
            temp_x = x_data[lower:upper]
            temp_y = y_data[lower:upper]
            temp_peak, temp_FWHM, temp_flag, unfit, fit = peak_helper(
                    temp_x,
                    temp_y,
                    num_peaks,
                    peak_shape)
            temp_peak = [i+lower for i in temp_peak]
            flag_list.extend(temp_flag)
            FWHM_list.extend(temp_FWHM)
            peak_list.extend(temp_peak)
            unfit_list[0].extend(temp_x)
            fit_list[0].extend(temp_x)
            for i in temp_x:
                if unfit is None:
                    unfit_list[1].append(0)
                    fit_list[1].append(0)
                else:
                    unfit_list[1].append(unfit(i))
                    fit_list[1].append(fit(i))

    else:
        peak_list, FWHM_list, flag_list, g_unfit, g_fit = peak_helper(
                        x_data,
                        y_data,
                        num_peaks,
                        peak_shape)
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
        diction['index'] = peak_list[i]
        diction['FWHM'] = FWHM_list[i]
        diction['flag'] = flag_list[i]
        return_list.append(diction)

    residual[0].extend(fit_list[0])
    temp_fit = np.array(fit_list[1])
    temp_y = np.array(y_data)
    resid = temp_y-temp_fit
    residual[1].extend(resid)

    return return_list, unfit_list, fit_list, residual, base_list

def peak_fit(array):
    array = np.array(array)
    assert array.ndim == 1, "Input array must be 1-dimensional"
    x = np.arange(array.shape[0])
    return_list, unfit_list, fit_list, residual, base_list = get_peaks(x, array, 2, 'g')
    peak_location = []
    for peak in return_list:
        peak_location.append(peak['index'])
    peak_location.sort()
    return np.array(peak_location)



def test():
    """
    This function will plot the peak locations for the entire data with path specified
    """
    file_path = "/Users/runbojiang/Desktop/AP-XPS-my/avg_array_3.npy"
    array = np.load(file_path)
    print(array.shape)
    sub_array = array[:300, :]
    np.save('test_array_300_1131.npy', sub_array)
    x = np.arange(array.shape[1])
    peak_locations = collections.defaultdict(list)
    start_time = time.time()
    # for i in range(array.shape[0]):
    for i in range(300):
        y = array[i, :]
        return_list, unfit_list, fit_list, residual, base_list = get_peaks(x, y, 2, 'g')
        for peak in return_list:
            peak_locations[i].append(peak['index'])

    print(time.time() - start_time, "s") # 28 s for 300 frames
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
    plt.show()

if __name__ == "__main__":
    test()