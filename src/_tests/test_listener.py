import asyncio
import contextlib
import threading
from unittest.mock import AsyncMock

import pytest

from tr_ap_xps.labview import XPSLabviewZMQListener, setup_zmq
from tr_ap_xps.schemas import XPSRawEvent, XPSStart, XPSStop
from tr_ap_xps.simulator.simulator import start

@contextlib.asynccontextmanager
async def run_simulator(num_frames: int = 1):
    thread = threading.Thread(target=start, kwargs={"repeat": False, "num_frames": num_frames})
    thread.start()
    try:
        yield thread
    finally:
        thread.join()  # Ensure the thread finishes before exiting the context
        print(f"Thread {thread.name} has finished.")


@pytest.fixture
async def mock_operator():
    return AsyncMock()


@pytest.mark.asyncio
async def test_listen_zmq_interface(mock_operator):
    zmq_socket = setup_zmq()  # Ensure setup_zmq supports async if needed

    async with run_simulator(num_frames=1):
        asyncio.sleep(2)
        listener = XPSLabviewZMQListener(mock_operator, zmq_socket)

        # Start the listener in an asyncio task
        listener_task = asyncio.create_task(listener.start())
        
        # Give the listener time to process messages
        await asyncio.sleep(5)

        # Stop the listener and wait for it to clean up
        await listener.stop()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass

        # Ensure process was called three times. We expect 1 event.
        assert mock_operator.process.call_count == 3

        # Validate that the arguments are instances of specific classes
        call_args = mock_operator.process.call_args_list
        assert isinstance(
            call_args[0][0][0], XPSStart
        ), f"First argument is not an instance of XPSStart: {call_args[0][0][0],"
        assert isinstance(
            call_args[1][0][0], XPSRawEvent
        ), f"Second argument is not an instance of XPSRawEvent: {call_args[1][0][0]}"
        assert isinstance(
            call_args[2][0][0], XPSStop
        ), f"Second argument is not an instance of XPSStop: {call_args[2][0][0]}"
