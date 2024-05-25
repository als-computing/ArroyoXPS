import contextlib
import subprocess
import sys
import threading
import time

import numpy as np

from tr_ap_xps.listener import ZMQImageListener


@contextlib.contextmanager
def run_publisher(command):
    "Run '/path/to/this/python -m ...'"
    process = subprocess.Popen(
        [sys.executable, "-m"] + command.split(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    yield process
    process.terminate()


def test_listen_zmq_interface():
    # Test that the listener can receive an image from the publisher
    # and that the image is the correct shape and dtype.
    # Starts a publisher as a sub processand a listener on a thread, sends an image from the publisher
    # dictionary to store the received image
    received_image = {}

    def got_an_image(frame_number: int, image: np.array):
        received_image["image"] = image
        received_image["frame_number"] = frame_number

    with run_publisher("tr_ap_xps.publisher"):
        image_dispatcher = ZMQImageListener(frame_function=got_an_image)
        thread = threading.Thread(target=image_dispatcher.start)
        thread.start()
        time.sleep(2)
        image_dispatcher.stop = True
        time.sleep(2)
        assert received_image["image"].shape == (10, 10)
        assert received_image["frame_number"]
