import os
import infinitymonkey_os as im_os
import pathlib
import requests
import json
from PIL import Image
from io import BytesIO
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import infinitymonkey_plot as im_plt
import copy

#
class TRAPXPStpx3:
    """
    Time-resolved ambient-pressure XPS configuration for TimePix3 at LBNL
    """
    #
    def __init__(self):
        # the URL of the running SERVAL (string)
        self.serverurl = 'http://localhost:8080' # 'http://192.168.50.216:8080' for remote control
        self.connection = None
        self.dashboard = None
        # configuration file names and corresponding info
        self.bpcFileName = 'pix-config.bpc'
        self.dacsFileName = 'pix-config.bpc.dacs'
        self.detectorConfig = None
        # location of files to write on disk
        self.path_raw = None
        self.path_img = None
        self.destination = None
        self.DA_fmt = '%04d'
        # debugging / display info
        self.print_response = True
        
    #
    # the following contains all functions from 
    #tpx3_example_01_connection.py
    #tpx3_example_02_settings.py
    #tpx3_example_03_acquisition.py
    #tpx3_example_04_preview.py
    #tpx3_example_05_rotation.py
    
    #
    def get_request(self, url, expected_status=200):
        response = requests.get(url=url)
        if response.status_code != expected_status:
            raise Exception("Failed GET request: {}, response: {} {}".format(url, response.status_code, response.text))
        #
        return response
    
    #
    def put_request(self, url, data, expected_status=200):
        response = requests.put(url=url, data=data)
        if response.status_code != expected_status:
            raise Exception("Failed PUT request: {}, response: {} {}".format(url, response.status_code, response.text))
        #
        return response
    
    #
    def check_connection(self):
        """
        Check connection with SERVAL
        Response "200" is expected when request has succeeded
        """
        response = self.get_request(url=self.serverurl, expected_status=200)
        self.connection = response.text
        print(f'connection (expected is "200"): {self.connection}\n')
        
    #
    def get_dashboard(self):
        """
        Get a dashboard of the running detector
        """
        response = self.get_request(url=self.serverurl + '/dashboard')
        self.dashboard = json.loads(response.text)
        print(f'dashboard:\n {self.dashboard}\n')
    
    #
    def get_detector_config(self):
        """
        Get the detector configuration from SERVAL
        """
        response = self.get_request(url=self.serverurl + '/detector/config')
        print('Detector Configuration from SERVAL : ' + response.text)
        #
        self.detectorConfig = json.loads(response.text)
        
    #
    def init_cam(self, bpc_file, dacs_file):
        """
        Load detector parameters required for operation, prints statuses
        
        bpc_file -- an absolute path to the binary pixel configuration file (string)
        dacs_file -- an absolute path to the text chips configuration file (string)
        """
        # load a binary pixel configuration exported by SoPhy, the file should exist on the server
        response = self.get_request(url=self.serverurl + '/config/load?format=pixelconfig&file=' + bpc_file)
        data = response.text
        print('Response of loading binary pixel configuration file: ' + data)
    
        #  ... and the corresponding DACs file
        response = self.get_request(url=self.serverurl + '/config/load?format=dacs&file=' + dacs_file)
        data = response.text
        print('Response of loading DACs file: ' + data)
    
        # set the detector configuration
        response = self.put_request(url=self.serverurl + '/detector/config',
                                    data=json.dumps(self.detectorConfig))
        data = response.text
        print('Response of loading Detector Configuration: ' + data)
    
    #
    def init_acquisition(self, trigger_mode="AUTOTRIGSTART_TIMERSTOP",
                         ntriggers=20, trigger_period=1.0, exposure_time=0.9):
        """
        Set the trigger mode, number of triggers, and the shutter timing for the detector

        trigger_mode -- for info on different modes see Trigger_mode_user_guide.pdf
        ntrig -- number of triggers to be executed (integer)
        trigger_period -- trigger period in seconds (float)
        exposure_time -- 'open time' of the shutter in seconds (float)
        """
    
        # Sets the number of triggers.
        self.detectorConfig["nTriggers"] = ntriggers
    
        # Set the trigger mode to be software-defined.
        self.detectorConfig["TriggerMode"] = trigger_mode
    
        # Sets the trigger period (time between triggers) in seconds.
        self.detectorConfig["TriggerPeriod"] = trigger_period
    
        # Sets the exposure time (time the shutter remains open) in seconds.
        self.detectorConfig["ExposureTime"] = exposure_time
    
        # Upload the Detector Configuration defined above
        response = self.put_request(url=self.serverurl + '/detector/config',
                                    data=json.dumps(self.detectorConfig))
        data = response.text
        print('Response of updating Detector Configuration: ' + data)
    
    #
    def acquisition_test(self):
        """
        Perform acquisition test
        """
        # Starting acquisition process
        response = self.get_request(url=self.serverurl + '/measurement/start')
        data = response.text
        print('Response of acquisition start: ' + data)
    
        # Example of measurement interruption
        taking_data = True
        while taking_data:
            self.dashboard = json.loads(self.get_request(url=self.serverurl + '/dashboard').text)
            # Stop measurement once Serval has collected all frames
            if self.dashboard["Measurement"]["Status"] == "DA_IDLE":
                taking_data = False
        #
        print('Acquisition is done.')
    
    #
    def simple_acquisition(self):
        """
        Perform simple acquisition
        """
        response = self.get_request(url=self.serverurl + '/measurement/start')
        data = response.text
        print('Response of acquisition start: ' + data)
    
    #
    def preview(self, ntrig=1):
        """
        Preview of collected data

        ntrig -- number of triggers to be executed (integer, default value is 1)
        """
        for i in range(ntrig):
            # Getting preview data. This is blocking, so it will wait until an image is ready.
            response = self.get_request(url=self.serverurl + '/measurement/image')
            image = Image.open(BytesIO(response.content))
            # Show the data in the image
            image.show()
            # Save a preview image
            image.save(pathlib.Path(os.path.join(self.path_raw, 'preview', 'test-preview{}.png'.format(i))))
    
    #######################################################################################################
    # combine the above functions into compact, easy to use methods for the user
    
    #
    def start_session(self, BiasVoltage=100, connectDetector=False):
        """
        - modify server URL to not run into trouble with internet?
        - check connection and print result
        - get and print dashboard
        - load bpc and dacs configuration files 
        - initialize detector (cam) [connectDetector=True]
        """        
        print('Server URL: ' + self.serverurl)
        
        # Check connection with SERVAL
        self.check_connection()
        # Retrieve the dashboard from SERVAL
        self.get_dashboard()
        
        # Get configuration files (from the working directory)
        bpcFile = os.path.join(os.getcwd(), self.bpcFileName)
        dacsFile = os.path.join(os.getcwd(), self.dacsFileName)

        # connect to detector
        if connectDetector == True:
            response = self.get_request(url=self.serverurl + '/detector/connect')
            print('Response of detector connect request: ' + response.text)
            
        self.get_detector_config() # get detector configuration from the server in JSON format
        
        # This is how to modify detector config values [type(detectorConfig) = Python dictionary]
        self.detectorConfig["BiasVoltage"] = BiasVoltage
        
        # Detector initialization with modified detector configuration values
        self.init_cam(bpcFile, dacsFile)
        #
        return None

    #
    def set_TR_path(self, path):
        """
        Set path of folder in which to save raw data in
        (images are saved in a "/img" subfolder)
        """
        self.path_raw = pathlib.Path(path)
        self.path_img = self.path_raw / 'img'
        
    #
    def set_TR_file(self, file_number, img=True, img_fmt="tiff", mode="count", int_size=0, verbose=False):
        """
        Destination configuration (Python dictionary) for the data output
        path: see/ use <set_TR_path(self, path)>
        raw tpx3 file is always acquired and saved
        
        img: save the image output (saved to "/img" subdirectory of <path>)
        img_fmt: image file type/ format (options are "tiff", )
        mode: build a frame from either "tot", "toa", "tof", or "count"
        int_size: 0/1 save individual images (one per trigger cycle), or
                  -1 average all, >1 (int) average the last N images
        """      
        destination_raw = {
            "Raw": [{
                # URI to a folder where to place the raw files.
                "Base": self.path_raw.as_uri(),
                # How to name the files for the various frames.
                "FilePattern": str(self.DA_fmt%file_number) + "_raw_",
                # write one file ('SINGLE_FILE') or a new file for every frame ('FRAME')
                #"SplitStrategy": "SINGLE_FILE" # seems to be the default now
            }]
        }
        destination_img = {
            "Image": [{
                # URI to a folder where to place the raw files.
                "Base": self.path_img.as_uri(),
                # How to name the files for the various frames.
                "FilePattern": str(self.DA_fmt%file_number) + "_img_",
                # What (image) format to write the files in.
                "Format": img_fmt,
                # What data to build a frame from (tot, toa, tof, count)
                "Mode": mode,
                # How to save images (0/1 ind., -1 average/sum all, or last N [>1])
                "IntegrationSize": -1,
                # If IntegrationSize != 0 or 1, should the sum or average be returned
                "IntegrationMode": "sum"
            }]
        }
    
        if img == False:
            self.destination = copy.deepcopy(destination_raw)
        elif img == True:
            self.destination = destination_raw | destination_img
    
        # Setting destination for the data output
        response = self.put_request(url=self.serverurl + '/server/destination',
                                    data=json.dumps(self.destination))
        data = response.text
        print('Response of uploading the Destination Configuration to SERVAL : ' + data)

        if verbose == True:
            # Getting destination for the data output from SERVAL
            response = self.get_request(url=self.serverurl + '/server/destination')
            data = response.text
            print('Selected destination : ' + data)
        #
        return None

    #
    def test_TR_acq(self):
        """
        Save a test file as file number 9999
        (with default <self.init_acquisition()> parameters)
        """
        self.set_TR_file(file_number = 9999, verbose=True)
        self.init_acquisition()
        self.acquisition_test()
        #
        return None
        
    #
    def acquire_TR_data(self, file_nr, mode="count", int_size=0,
                        trigger_mode="AUTOTRIGSTART_TIMERSTOP",
                        ntriggers=20, trigger_period=0.25, exposure_time=0.10):
        """
        
        """
        # destination
        self.set_TR_file(file_nr, mode="count", int_size=0)
        # initialize acquisition
        self.init_acquisition(trigger_mode, ntriggers, trigger_period, exposure_time)
        # acquire data
        self.acquisition_test()
        
        # start
        #response = self.get_request(url=self.serverurl + '/measurement/start')
        #print('Response of acquisition start: ' + response.text)
        # STOP COMES TO EARLY, NO DATA ACQUIRED
        # stop
        #response = self.get_request(url=self.serverurl + '/measurement/stop')
        #print('Response of acquisition stop: ' + response.text)
        #
        return None
        
    #
    def stop_session(self, shutdownServer=False):
        """
        Disconnect from detector and (optionally) shut down server
        """
        # disconnect from detector
        response = self.get_request(url=self.serverurl + '/detector/disconnect')
        print('Response of detector disconnect request: ' + response.text)
        # shut down server
        if shutdownServer == True:
            response = self.get_request(url=self.serverurl + '/server/shutdown')
            print('Response of server shutdown request: ' + response.text)
        #
        return None

    #
    # HELPER FUNCTIONS / Data analysis
    #
    
    #
    def sum_all_imgs(self, file_number):
        """
        
        """
        files = im_os.find_files(path = self.path_img,
                                 file_type = 'tiff',
                                 search_str = str(self.DA_fmt%file_number),
                                 show_info = 0)
        # sum all
        img_sum = np.zeros([256, 256, 4])
        for file in files: # load images
            img_sum += mpimg.imread(self.path_img / file)
        # plot average
        img_avg = img_sum/len(files)
        fig, ax = plt.subplots(1, 1, dpi=100)
        plt.imshow(img_avg); plt.show()
        # bin
        spectrum = np.sum(img_avg[:,:,0], axis=1)
        im_plt.plot_1D([spectrum,], dpi_plot=100)
        # calculate total counts per trigger
        counts = np.sum(spectrum)
        #
        return [img_avg, spectrum, counts]
        
#
#
#