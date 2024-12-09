import asyncio
import contextlib
import subprocess
import sys
from unittest.mock import AsyncMock

import pytest

from tr_ap_xps.labview import XPSLabviewZMQListener, setup_zmq
from tr_ap_xps.schemas import XPSRawEvent, XPSStart


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


@pytest.fixture
def mock_operator():
    return AsyncMock()


@pytest.mark.asyncio
async def test_listen_zmq_interface(mock_operator):
    async with run_simulator("tr_ap_xps.simulator"):
        zmq_socket = setup_zmq()  # Ensure setup_zmq supports async if needed
        listener = XPSLabviewZMQListener(mock_operator, zmq_socket)

        # Start the listener in an asyncio task
        listener_task = asyncio.create_task(listener.start())

        # Give the listener time to process messages
        await asyncio.sleep(1)

        # Stop the listener and wait for it to clean up
        await listener.stop()
        await listener_task

        # Ensure process was called three times
        assert mock_operator.process.call_count == 3

        # Validate that the arguments are instances of specific classes
        for call_args in mock_operator.process.call_args_list:
            assert isinstance(
                call_args[0][0], XPSStart
            ), f"First argument is not an instance of ExpectedClass1: {call_args[0][0]}"
            assert isinstance(
                call_args[0][1], XPSRawEvent
            ), f"Second argument is not an instance of ExpectedClass2: {call_args[0][1]}"
