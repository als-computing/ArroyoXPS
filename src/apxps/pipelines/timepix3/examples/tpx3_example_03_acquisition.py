#!/usr/bin/python
# -*- coding: utf-8 -*-


"""
Prepare a detector for acquisition process, starting and interrupting acquisition

"""

# Libs
import os
import pathlib
import requests
import json

__author__ = "Amsterdam Scientific Instruments"
__version__ = "3"
__email__ = "support@amscins.com"


def get_request(url, expected_status=200):
    response = requests.get(url=url)
    if response.status_code != expected_status:
        raise Exception("Failed GET request: {}, response: {} {}".format(url, response.status_code, response.text))

    return response


def put_request(url, data, expected_status=200):
    response = requests.put(url=url, data=data)
    if response.status_code != expected_status:
        raise Exception("Failed PUT request: {}, response: {} {}".format(url, response.status_code, response.text))

    return response


def check_connection(serverurl):
    """Check connection with SERVAL

    Keyword arguments:
    serverurl -- the URL of the running SERVAL (string)
    """

    # Response "200" is expected when request has succeeded
    get_request(url=serverurl, expected_status=200)


def get_dashboard(serverurl):
    """Get a dashboard of the running detector

    Keyword arguments:
    serverurl -- the URL of the running SERVAL (string)
    """
    response = get_request(url=serverurl + '/dashboard')
    data = response.text
    dashboard = json.loads(data)
    return dashboard


def init_cam(serverurl, bpc_file, dacs_file):
    """Load detector parameters required for operation, prints statuses

    Keyword arguments:
    serverurl -- the URL of the running SERVAL (string)
    bpc_file -- an absolute path to the binary pixel configuration file (string)
    dacs_file -- an absolute path to the text chips configuration file (string)
    """
    # load a binary pixel configuration exported by SoPhy, the file should exist on the server
    response = get_request(url=serverurl + '/config/load?format=pixelconfig&file=' + bpc_file)
    data = response.text
    print('Response of loading binary pixel configuration file: ' + data)

    #  .... and the corresponding DACs file
    response = get_request(url=serverurl + '/config/load?format=dacs&file=' + dacs_file)
    data = response.text
    print('Response of loading DACs file: ' + data)


def init_acquisition(serverurl, detector_config, ntriggers=1, trigger_period=0.5, exposure_time=0.10):
    """Set the number of triggers and the shutter timing for the detector

    Keyword arguments:
    serverurl -- the URL of the running SERVAL (string)
    detector_config -- a dictionary with Detector Configuration data (Python dictionary)
    ntrig -- number of triggers to be executed (integer, default value is 1)
    trigger_period -- trigger period in seconds (float, default value is 0.5)
    exposure_time -- 'open time' of the shutter in seconds (integer, default value is 0.10)
    """

    # Sets the number of triggers.
    detector_config["nTriggers"] = ntriggers

    # Set the trigger mode to be software-defined.
    detector_config["TriggerMode"] = "AUTOTRIGSTART_TIMERSTOP"

    # Sets the trigger period (time between triggers) in seconds.
    detector_config["TriggerPeriod"] = trigger_period

    # Sets the exposure time (time the shutter remains open) in seconds.
    detector_config["ExposureTime"] = exposure_time

    # Upload the Detector Configuration defined above
    response = put_request(url=serverurl + '/detector/config', data=json.dumps(detector_config))
    data = response.text
    print('Response of updating Detector Configuration: ' + data)


def acquisition_test(serverurl):
    """Perform acquisition

    Keyword arguments:
    serverurl -- the URL of the running SERVAL (string)
    """
    # Starting acquisition process
    response = get_request(url=serverurl + '/measurement/start')
    data = response.text
    print('Response of acquisition start: ' + data)

    # Example of measurement interruption
    taking_data = True
    while taking_data:
        dashboard = json.loads(get_request(url=serverurl + '/dashboard').text)
        # Stop measurement once Serval has collected all frames
        if dashboard["Measurement"]["Status"] == "DA_IDLE":
            taking_data = False

# Example of usage
if __name__ == '__main__':
    # Define server url.
    # Localhost is used when SERVAL is running on the same computer, but SERVAL can also be accessed remotely.
    serverurl = 'http://localhost:8080'
    # serverurl =  'http://192.168.50.216:8080'

    # Check connection with SERVAL
    check_connection(serverurl)

    # Retrieve the dashboard from SERVAL
    dashboard = get_dashboard(serverurl)
    # Print selected parameter from the dashboard
    print('Server Software Version:', dashboard['Server']['SoftwareVersion'])
    # Print whole dashboard
    print('Dashboard:', dashboard)

    # Change file paths to match the paths of the files on the server:
    # For example, a Linux path:
    # bpcFile = '/home/asi/tpx3-demo.bpc
    # dacsFile = '/home/asi/tpx3-demo.dacs'
    # And on Windows:
    # bpcFile = 'C:\\Users\\ASI\\tpx3-demo.bpc'
    # dacsFile = 'C:\\Users\\ASI\\tpx3-demo.dacs'
    # The following requires the files to be in the working directory:
    bpcFile = os.path.join(os.getcwd(), 'tpx3-demo.bpc')
    dacsFile = os.path.join(os.getcwd(), 'tpx3-demo.dacs')

    # Detector initialization with bpc and DACs
    init_cam(serverurl, bpcFile, dacsFile)

    # Example of getting the detector configuration from the server in JSON format
    response = get_request(url=serverurl + '/detector/config')
    data = response.text
    print('Response of getting the Detector Configuration from SERVAL: ' + data)

    # Converting detector configuration data from JSON to Python dictionary and modifying values
    detectorConfig = json.loads(data)
    detectorConfig["BiasVoltage"] = 100
    detectorConfig["BiasEnabled"] = True

    # Setting the timing for the acquisition     
    init_acquisition(serverurl, detectorConfig, 20, 0.500, 0.010)

    # Getting the updated detector configuration  from SERVAL
    response = get_request(url=serverurl + '/detector/config')
    data = response.text
    print('Response of getting the updated Detector Configuration from SERVAL : ' + data)

    # Example of destination configuration (Python dictionary) for the data output
    destination = {
        "Raw": [{
            # URI to a folder where to place the raw files.
            "Base": pathlib.Path(os.path.join(os.getcwd(), 'data')).as_uri(),
            # How to name the files for the various frames.
            "FilePattern": "raw%Hms_",
        }],
        "Image": [{
            # URI to a folder where to place the raw files.
            "Base": pathlib.Path(os.path.join(os.getcwd(), 'data')).as_uri(),
            # How to name the files for the various frames.
            "FilePattern": "f%Hms_",
            # What (image) format to write the files in.
            "Format": "tiff",
            # What data to build a frame from (tot, toa, tof, count)
            "Mode": "tot"
        }]
    }

    # Setting destination for the data output
    response = put_request(url=serverurl + '/server/destination', data=json.dumps(destination))
    data = response.text
    print('Response of uploading the Destination Configuration to SERVAL : ' + data)

    # Getting destination for the data output from SERVAL
    response = get_request(url=serverurl + '/server/destination')
    data = response.text
    print('Selected destination : ' + data)

    # Running acquisition process
    acquisition_test(serverurl)

    print('Ready.')
