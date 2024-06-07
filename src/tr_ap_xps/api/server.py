import asyncio
import base64
import io
import logging

import numpy as np
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

from ..log_utils import setup_logger
from .zmq_subscriber import subscriber

logger = logging.getLogger(__name__)
setup_logger(logger)

app = FastAPI()

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
            result = await subscriber.receive_message()
            # data = {
            #     "description": "name tbd",
            #     "image": [result.integrated_frame, result.ifft, result.vfft],
            #     "plots": [

            #     ]

            # }
            data = {"description": "", "images": [], "plots": []}
            # Generate 3 random RGB images
            # img_types = ["raw", "vfft", "ifft"]
            # plot_types = ["sum", "fitted"]

            raw_img = array_to_jpeg(result.integrated_frame)
            ifft_img = array_to_jpeg(result.ifft)
            vfft_img = array_to_jpeg(result.vfft)
            data["images"] = [raw_img, ifft_img, vfft_img]
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

    uvicorn.run("tr_ap_xps.api.server:app", host="127.0.0.1", port=8001, reload=True)
