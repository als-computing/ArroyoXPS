import asyncio
import base64
import io
import json
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


def buffer_to_jpeg(arr_buffer, shape: list, dtype: str):
    shape = tuple(shape)
    nd_arr = np.frombuffer(arr_buffer, dtype=dtype).reshape(shape)
    img = Image.fromarray(nd_arr, "RGB")
    # Convert image to base64
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return img_str


def peaks_output(json_str):
    #     [
    # {"x": 235, "h": 433.3: "fwhm": 4334},
    # {"x": 235, "h": 433.3: "fwhm": 4334}
    # ]
    obj = json.loads(json_str)
    data = [{"x": data[0], "h": data[1], "fwhm": data[2]} for data in obj["data"]]
    return data


@app.websocket("/simImages")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            result = await subscriber.receive_message()
            integrated_frame = buffer_to_jpeg(
                result.integrated_frame,
                result.result_info["shape"],
                result.result_info["dtype"],
            )
            ifft = buffer_to_jpeg(
                result.ifft,
                result.result_info["ifft_shape"],
                result.result_info["ifft_dtype"],
            )
            vfft = buffer_to_jpeg(
                result.vfft,
                result.result_info["vfft_shape"],
                result.result_info["vfft_dtype"],
            )
            # sum_json = df_to_json(result.sum)
            detected_peaks = json.dumps(peaks_output(result.detected_peaks))

            data = {
                "frame_number": result.result_info["frame_number"],
                "integrated_frame": integrated_frame,
                "detected_peaks": detected_peaks,
                "vfft": vfft,
                "ifft": ifft,
            }
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
