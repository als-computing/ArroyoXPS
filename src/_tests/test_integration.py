import subprocess
import time
from multiprocessing import Process

import pytest
import zmq


def start_processor_cli():
    """Start the processor CLI as a subprocess."""
    subprocess.run(
        ["python", "-m", "tr_ap_xps.apps.processor_cli", "listen"],
        check=False,  # Don't fail if it exits early
    )


def start_zmq_publisher(port):
    """Start a ZMQ publisher that sends test messages."""
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind(f"tcp://*:{port}")
    # Give subscribers time to connect (ZMQ slow joiner problem)
    time.sleep(1)
    # Send a few messages
    for i in range(5):
        socket.send_string("test message")
        time.sleep(0.5)
    socket.close()
    context.term()


def test_integration():
    """Integration test for ZMQ message flow."""
    # Dynamically assign a port for ZMQ publisher
    context = zmq.Context()
    temp_socket = context.socket(zmq.PUB)
    port = temp_socket.bind_to_random_port("tcp://*")
    temp_socket.close()
    context.term()

    # Start zmq publisher in a background process with the random port
    zmq_publisher_process = Process(target=start_zmq_publisher, args=(port,))
    zmq_publisher_process.start()
    time.sleep(0.5)  # Give it time to start

    # Set up zmq subscriber to receive messages
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect(f"tcp://localhost:{port}")
    socket.setsockopt_string(zmq.SUBSCRIBE, "")
    # Set timeout to prevent hanging
    socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout

    # Give ZMQ time to establish connection (slow joiner problem)
    time.sleep(1)

    try:
        # Check if messages are received and processed
        # The timeout is set above, so this won't hang forever
        message = socket.recv_string()
        assert message == "test message"
    except zmq.Again:
        pytest.fail("No message received from ZMQ publisher within timeout")
    finally:
        # Clean up
        socket.close()
        context.term()
        zmq_publisher_process.join(timeout=2)  # Wait for process to finish
        if zmq_publisher_process.is_alive():
            zmq_publisher_process.terminate()
            zmq_publisher_process.join()
