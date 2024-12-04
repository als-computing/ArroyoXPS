import subprocess
import time
from multiprocessing import Process

import zmq


def start_processor_cli():
    subprocess.run(["python", "processor_cli.py"])


def start_zmq_publisher():
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind("tcp://*:5555")
    while True:
        socket.send_string("test message")
        time.sleep(1)


def start_tiled_server():
    subprocess.run(["python", "tiled_server.py"])


def test_integration():
    # Start processor_cli in a background process
    processor_cli_process = Process(target=start_processor_cli)
    processor_cli_process.start()
    time.sleep(2)  # Give it time to start

    # Start zmq publisher in a background process
    zmq_publisher_process = Process(target=start_zmq_publisher)
    zmq_publisher_process.start()
    time.sleep(2)  # Give it time to start

    # Start tiled server in a background process
    tiled_server_process = Process(target=start_tiled_server)
    tiled_server_process.start()
    time.sleep(2)  # Give it time to start

    # Set up zmq subscriber to receive messages
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect("tcp://localhost:5555")
    socket.setsockopt_string(zmq.SUBSCRIBE, "")
    #
    # Check if messages are received and processed
    message = socket.recv_string()
    assert message == "test message"

    # Clean up
    processor_cli_process.terminate()
    zmq_publisher_process.terminate()
    tiled_server_process.terminate()
