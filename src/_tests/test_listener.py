import asyncio
import contextlib
import subprocess
import sys
from unittest.mock import AsyncMock

import pytest

from tr_ap_xps.labview import XPSLabviewZMQListener, setup_zmq
from tr_ap_xps.schemas import XPSRawEvent, XPSStart, XPSStop


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
    # Start the listener coroutine

    with run_simulator("tr_ap_xps.simulator.simulator --no-repeat --num-frames 5"):
        zmq_socket = setup_zmq()
        listener = XPSLabviewZMQListener(mock_operator, zmq_socket)
        listener_task = await asyncio.create_task(listener.start())
        # Give some time for the listener to start and process messages
        await asyncio.sleep(7)

        # Stop the listener and wait for it to complete
        await listener.stop()
        await listener_task

        # Verify the specific arguments for each call
        assert mock_operator.process.call_count == 3

        # Verify the arguments are instances of specific classes
        for call_args in mock_operator.process.call_args_list:
            assert isinstance(
                call_args[0][0], XPSStart
            ), f"First argument is not an instance of XPSStart: {call_args[0][0]}"
            assert isinstance(
                call_args[0][1], XPSRawEvent
            ), f"Second argument is not an instance of XPSRawEvent: {call_args[0][1]}"
            assert isinstance(
                call_args[0][1], XPSStop
            ), f"Second argument is not an instance of XPSStop: {call_args[0][1]}"
