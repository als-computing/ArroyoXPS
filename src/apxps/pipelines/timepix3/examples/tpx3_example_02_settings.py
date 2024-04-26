#!/usr/bin/python
# -*- coding: utf-8 -*-


"""
Detector initialization with modified System Configuration values
This example code does not contain exceptions handling in all required places
"""

# Libs
import os
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


def init_cam(serverurl, detector_config, bpc_file, dacs_file):
    """Load detector parameters required for operation, prints statuses

    Keyword arguments:
    serverurl -- the URL of the running SERVAL (string)
    detector_config -- the Detector Config to upload (dictionary)
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

    # set the detector configuration
    response = put_request(url=serverurl + '/detector/config', data=json.dumps(detector_config))
    data = response.text
    print('Response of loading Detector Configuration: ' + data)

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

    # Example of getting the detector configuration from the server in JSON format
    response = get_request(url=serverurl + '/detector/config')
    data = response.text
    print('Response of getting the Detector Configuration from SERVAL: ' + data)

    # Converting detector configuration data from JSON to Python dictionary and modifying values
    detectorConfig = json.loads(data)
    detectorConfig["BiasVoltage"] = 100
    detectorConfig["BiasEnabled"] = True

    # Detector initialization with modified detector configuration values
    init_cam(serverurl, detectorConfig, bpcFile, dacsFile)

    # Getting the updated detector configuration  from SERVAL
    response = get_request(url=serverurl + '/detector/config')
    data = response.text
    print('Response of getting the updated Detector Configuration from SERVAL : ' + data)

    print('Ready.')
