==== How to run ====

Test detector connection to server:
$ ping 192.168.1.10 (1 GB connection) or ping 192.168.100.10 (10 GB connection)

Run the server:
$ java -jar serval-3.0.0.jar

Test whether client can contact to server, for example:
$ ping localhost:8080 or browse to localhost:8080 in your webbrowser

Python 3 and supporting packages have to be installed
Please be aware to change the directories in the python files with the correct configuration file(s) and destination path.
$ pip install -r requirements.txt

Run a script on the command line, for example:
$ python tpx3_example_01.py



==== Example Files ====

Example: Checking connection with SERVAL
$ python tpx3_example_01_connection.py

Example: Load config & calibration
$ python tpx3_example_02_settings.py

Example: Start measurement
$ python tpx3_example_03_acquisition.py

Example: Collect preview and save measurement data
$ python tpx3_example_04_preview.py

Example: Rotate or flip output images
$ python tpx3_example_05_rotation.py

