#!/usr/bin/python
# -*- coding: utf-8 -*-


"""
Test connection of the TPX3 detector to SERVAL
This example code does not contain exceptions handling in all required places
"""

# Libs
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

    print('Ready.')
