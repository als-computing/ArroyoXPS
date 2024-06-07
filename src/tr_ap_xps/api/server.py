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

def buffer_to_jpeg_scaled_down(arr_buffer, shape: list, dtype: str):
    shape = tuple(shape)
    nd_arr = np.frombuffer(arr_buffer, dtype=dtype).reshape(shape)
    img = Image.fromarray(nd_arr, "RGB")

    #Scale down the image. The React client uses a size of 512x512
    client_size = 512

    #current frame image dimensions
    width, height = img.size

    #determine new dimensions
    if width >= height:
        new_width = client_size
        new_height = int(height / width * client_size)
    else:
        #we shouldn't be entering this else statement since our height fills up compared to fixed width
        new_width = int(width / height * client_size)
        new_height = client_size

    #resize image
    img = img.resize((new_width, new_height), Image.ANTIALIAS)


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
            raw = buffer_to_jpeg(
                result.raw,
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
            detected_peaks = json.dumps(peaks_output(result.fitted))

            """ data = {
                "result_info": result.result_info,
                "frame_number": result.result_info["frame_number"],
                "raw": raw,
                "fitted": detected_peaks,
                "vfft": vfft,
                "ifft": ifft,
            } """

            # send basic info
            await websocket.send_json({
                "result_info": result.result_info,
                "frame_number": result.result_info["frame_number"]
            })

            # send image data separately to client memory issues
            await websocket.send_json({"raw": raw,})
            await websocket.send_json({"fitted": detected_peaks})
            await websocket.send_json({"vfft": vfft})
            await websocket.send_json({"ifft": ifft})


            # # Send all data
            #await websocket.send_json(data)
            await asyncio.sleep(0.1)  # Sending 10 new images every second
    except Exception as e:
        print("Error:", e)
    finally:
        await websocket.close()

@app.websocket("/simImagesScaled")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            result = await subscriber.receive_message()
            raw = buffer_to_jpeg_scaled_down(
                result.raw,
                result.result_info["shape"],
                result.result_info["dtype"],
            )
            ifft = buffer_to_jpeg_scaled_down(
                result.ifft,
                result.result_info["ifft_shape"],
                result.result_info["ifft_dtype"],
            )
            vfft = buffer_to_jpeg_scaled_down(
                result.vfft,
                result.result_info["vfft_shape"],
                result.result_info["vfft_dtype"],
            )
            # sum_json = df_to_json(result.sum)
            detected_peaks = json.dumps(peaks_output(result.fitted))

            # send basic info
            await websocket.send_json({
                "result_info": result.result_info,
                "frame_number": result.result_info["frame_number"]
            })

            # send image data separately to client memory issues
            await websocket.send_json({"raw": raw,})
            await websocket.send_json({"fitted": detected_peaks})
            await websocket.send_json({"vfft": vfft})
            await websocket.send_json({"ifft": ifft})


            await asyncio.sleep(0.1)  # Sending 10 new images every second
    except Exception as e:
        print("Error:", e)
    finally:
        await websocket.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("tr_ap_xps.api.server:app", host="127.0.0.1", port=8001, reload=True)
