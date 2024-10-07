import contextlib
import subprocess
import sys
import threading
import time

import numpy as np

from tr_ap_xps.labview_listener import XPSLabviewZMQListener


@contextlib.contextmanager
def run_simulator(command):
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
    run = {}

    def start(start_doc: dict):
        run["start"] = start_doc

    def event(image_info: dict, image: np.array):
        run["image_info"] = image_info
        run["image"] = image

    def stop(stop_doc: np.array):
        run["stop"] = stop_doc

    with run_simulator("tr_ap_xps.simulator"):
        image_dispatcher = XPSLabviewZMQListener(
            start_function=start, event_function=event, stop_function=stop
        )
        thread = threading.Thread(target=image_dispatcher.start)
        thread.start()
        time.sleep(2)
        image_dispatcher.stop = True
        time.sleep(2)
        # TODO: fix test
        # assert run["image"].shape == (10, 10)
        # assert run["frame_number"]
