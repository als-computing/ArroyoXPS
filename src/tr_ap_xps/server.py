import asyncio
import base64
from contextlib import asynccontextmanager
import io
import logging
import os
import queue
import threading
import time

import numpy as np
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image


from tiled.client import from_uri, node

from .beamline_events import Event, Start, Stop
from .labview import LabviewListener
from .log import setup_logger
from .processor import XPSProcessor, Result
from .shared_queue import raw_message_queue, processed_message_queue



setup_logger()
logger = logging.getLogger("tr-ap-xps.cli")



def start_listener(listener: LabviewListener):
    listener.start()


def monitor_runs(runs_node: node):
    message = None
  
    while True:
        try:
            message = raw_message_queue.get(
                timeout=1
            )  # Timeout to prevent indefinite blocking
        except queue.Empty:
            pass
        if not message:
            continue
        try:
            if isinstance(message, Start):
                processor = XPSProcessor(
                    runs_node,
                    message.metadata["scan_name"],
                    message.metadata["frame_per_cycle"],
                )
                continue

            if isinstance(message, Event):
                result = processor.process_frame(message)
                if result:
                    if processed_message_queue.qsize() > 100:
                        processed_message_queue.get()

                    processed_message_queue.put(result)
                continue
            if isinstance(message, Stop):
                processor = None
        except Exception as e:
            logger.exception(e)
        time.sleep(0.01)

 
@asynccontextmanager
async def lifespan(app: FastAPI):
    # logger.setLevel(log_level.upper())
    # logger.debug("DEBUG LOGGING SET")
    # logger.info(f"zmq_pub_address: {zmq_pub_address}")
    # logger.info(f"zmq_pub_port: {zmq_pub_port}")


    tiled_token = os.getenv("TILED_SINGLE_USER_API_KEY")
    tiled_client = from_uri("http://localhost:8000/api", api_key=tiled_token)
    if tiled_client.get("runs") is None:
        tiled_client.create_container("runs")
    runs_node = tiled_client["runs"]

    # labview_listener = LabviewListener(
    #     zmq_pub_address=zmq_pub_address, zmq_pub_port=zmq_pub_port
    # )
    labview_listener = LabviewListener()
    labview_thread = threading.Thread(
        name="LabviewListenerThread", target=start_listener, args=(labview_listener,)
    )
    labview_thread.start()

    processor_thread = threading.Thread(
        name="ProcessorThread", target=monitor_runs, args=(runs_node,)
    )
    processor_thread.start()

    yield

app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:3000",
    "http://localhost:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)


def array_to_jpeg(arr: np.ndarray):
    img = Image.fromarray(arr, "RGB")
    # Convert image to base64
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return img_str

@app.websocket("/simImages")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            result = None
            try:
                # result = await asyncio.to_thread(processed_message_queue.get, timeout=1) 
                result = processed_message_queue.get(timeout=1)
            except queue.Empty:
                pass
            if result is None:
                continue
            # data = {
            #     "description": "name tbd",
            #     "image": [result.integrated_frame, result.ifft, result.vfft],
            #     "plots": [

            #     ]

            # }
            data = {"description": "", "images": [], "plots": []}
            # Generate 3 random RGB images
            img_types = ["raw", "vfft", "ifft"]
            plot_types = ["sum", "fitted"]

            raw_img = array_to_jpeg(result.integrated_frame)
            ifft_img = array_to_jpeg(result.ifft)
            vfft_img = array_to_jpeg(result.vfft)
            data['images'] = [raw_img, ifft_img, vfft_img]
            # for i in range(2):
            #     gaussianPlot = {
            #         "X": np.random.randint(20) + 5,
            #         "H": np.random.randint(20) + 5,
            #         "FWHM": np.random.randint(20) + 1,
            #     }
            #     plot = {"terms": gaussianPlot, "key": plot_types[i]}
            #     data["plots"].append(plot)
            # provide description
            data["description"] = "3 sample images and 2 sample plots"

            # # Send all data
            await websocket.send_json(data)
            await asyncio.sleep(0.1)  # Sending 10 new images every second
    except Exception as e:
        print("Error:", e)
    finally:
        await websocket.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("tr_ap_xps.server:app", host="127.0.0.1", port=8001, reload=True)

# if __name__ == "__main__":
#     cli_app()
