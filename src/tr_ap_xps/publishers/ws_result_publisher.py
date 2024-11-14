import asyncio
import base64
import io
import json
import logging
from typing import Union

import numpy as np
import pandas as pd
import websockets
from arroyo.publisher import Publisher
from PIL import Image

from ..schemas import XPSResult, XPSStart, XPSResultStop

logger = logging.getLogger(__name__)


class XPSWSResultPublisher(Publisher):
    """
    A publisher class for sending XPSResult messages over a web sockets.

    """

    websocket_server = None
    connected_clients = set()

    def __init__(self):
        super().__init__()

    async def start(self, host: str = "localhost", port: int = 8765):
        # Use partial to bind `self` while matching the expected handler signature
        server = await websockets.serve(self.websocket_handler, host, port, )
        logger.info(f"Websocket server started at ws://{host}:{port}")
        await server.wait_closed()

    async def publish(self, message: XPSResult) -> None:
        if self.connected_clients:  # Only send if there are clients connected
            asyncio.gather(
                *(self.publish_ws(client, message) for client in self.connected_clients)
            )

    async def publish_ws(
        self,
        #  client: websockets.client.ClientConnection,
        client,
        message: Union[XPSResult | XPSStart | XPSResultStop],
    ) -> None:
        if isinstance(message, XPSResultStop):
            return

        if isinstance(message, XPSStart):
            await client.send(json.dumps(message.model_dump()))
            return

        raw = buffer_to_jpeg(message.integrated_frames.array)
        ifft = buffer_to_jpeg(message.ifft.array)
        vfft = buffer_to_jpeg(message.vfft.array)

        # sum_json = df_to_json(result.sum)
        detected_peaks = json.dumps(peaks_output(message.detected_peaks.df))

        # send basic info
        # await client .send_json(
        #     {
        #         "result_info": message.result_info,
        #         "frame_number": message.result_info["frame_number"],
        #     }
        # )

        # send image data separately to client memory issues
        await client.send(json.dumps({"raw": raw}))
        await client.send(json.dumps({"fitted": detected_peaks}))
        await client.send(json.dumps({"vfft": vfft}))
        await client.send(json.dumps({"ifft": ifft}))

    async def websocket_handler(self, websocket):
        logger.info(f"New connection from {websocket.remote_address}")
        self.connected_clients.add(websocket)
        try:
            # Keep the connection open and do nothing until the client disconnects
            await websocket.wait_closed()
        finally:
            # Remove the client when it disconnects
            self.connected_clients.remove(websocket)
            logger.info("Client disconnected")


def buffer_to_jpeg(arra_: np.ndarray):
    if arra_.dtype != np.uint8:
        arra_ = (arra_ * 255).astype(np.uint8)

    img = Image.fromarray(arra_, "L")
    # Convert image to base64
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str


def peaks_output(peaks: pd.DataFrame):
    #     [
    # {"x": 235, "h": 433.3: "fwhm": 4334},
    # {"x": 235, "h": 433.3: "f whm": 4334}
    # ]
    peaks.columns = ["x", "h", "fwhm"]
    return peaks.to_dict(orient="records")


# import asyncio
# import base64
# import io
# import json
# import logging

# import numpy as np
# from fastapi import FastAPI, WebSocket
# from fastapi.middleware.cors import CORSMiddleware
# from PIL import Image

# from ..log_utils import setup_logger
# from .result_subscriber import subscriber

# logger = logging.getLogger("ws-publisher")
# setup_logger(logger)


# app = FastAPI()
# origins = [
#     "http://localhost",
#     "http://localhost:8080",
#     "http://localhost:3000",
#     "http://localhost:3001",
# ]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# def buffer_to_jpeg(arr_buffer, shape: list, dtype: str):
#     shape = tuple(shape)
#     nd_arr = np.frombuffer(arr_buffer, dtype=dtype).reshape(shape)
#     img = Image.fromarray(nd_arr, "L")
#     # Convert image to base64
#     buffered = io.BytesIO()
#     img.save(buffered, format="JPEG")
#     img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

#     return img_str

# def buffer_to_jpeg_scaled_down(arr_buffer, shape: list, dtype: str):
#     shape = tuple(shape)
#     nd_arr = np.frombuffer(arr_buffer, dtype=dtype).reshape(shape)
#     img = Image.fromarray(nd_arr, "RGB")

#     # Scale down the image. The React client uses a size of 512x512
#     client_size = 512

#     # current frame image dimensions
#     width, height = img.size

#     # determine new dimensions
#     if width >= height:
#         new_width = client_size
#         new_height = int(height / width * client_size)
#     else:
#         # we shouldn't be entering this else statement since our height fills up compared to fixed width
#         new_width = int(width / height * client_size)
#         new_height = client_size

#     # resize image
#     img = img.resize((new_width, new_height), Image.ANTIALIAS)

#     # Convert image to base64
#     buffered = io.BytesIO()
#     img.save(buffered, format="JPEG")
#     img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

#     return img_str


# def peaks_output(json_str):
#     #     [
#     # {"x": 235, "h": 433.3: "fwhm": 4334},
#     # {"x": 235, "h": 433.3: "fwhm": 4334}
#     # ]
#     obj = json.loads(json_str)
#     data = [{"x": data[0], "h": data[1], "fwhm": data[2]} for data in obj["data"]]
#     return data


# @app.websocket("/simImages")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     try:
#         while True:
#             result = await subscriber.receive_message()
#             raw = buffer_to_jpeg(
#                 result.raw,
#                 result.result_info["shape"],
#                 result.result_info["dtype"],
#             )
#             ifft = buffer_to_jpeg(
#                 result.ifft,
#                 result.result_info["ifft_shape"],
#                 result.result_info["ifft_dtype"],
#             )
#             vfft = buffer_to_jpeg(
#                 result.vfft,
#                 result.result_info["vfft_shape"],
#                 result.result_info["vfft_dtype"],
#             )
#             # sum_json = df_to_json(result.sum)
#             detected_peaks = json.dumps(peaks_output(result.fitted))

#             """ data = {
#                 "result_info": result.result_info,
#                 "frame_number": result.result_info["frame_number"],
#                 "raw": raw,
#                 "fitted": detected_peaks,
#                 "vfft": vfft,
#                 "ifft": ifft,
#             } """

#             # send basic info
#             await websocket.send_json(
#                 {
#                     "result_info": result.result_info,
#                     "frame_number": result.result_info["frame_number"],
#                 }
#             )

#             # send image data separately to client memory issues
#             await websocket.send_json(
#                 {
#                     "raw": raw,
#                 }
#             )
#             await websocket.send_json({"fitted": detected_peaks})
#             await websocket.send_json({"vfft": vfft})
#             await websocket.send_json({"ifft": ifft})

#             # # Send all data
#             # await websocket.send_json(data)
#             await asyncio.sleep(0.1)  # Sending 10 new images every second
#     except Exception as e:
#         print("Error:", e)
#     finally:
#         await websocket.close()


# # @app.websocket("/simImagesScaled")
# # async def websocket_endpoint(websocket: WebSocket):
# #     await websocket.accept()
# #     try:
# #         while True:
# #             result = await subscriber.receive_message()
# #             raw = buffer_to_jpeg_scaled_down(
# #                 result.raw,
# #                 result.result_info["shape"],
# #                 result.result_info["dtype"],
# #             )
# #             ifft = buffer_to_jpeg_scaled_down(
# #                 result.ifft,
# #                 result.result_info["ifft_shape"],
# #                 result.result_info["ifft_dtype"],
# #             )
# #             vfft = buffer_to_jpeg_scaled_down(
# #                 result.vfft,
# #                 result.result_info["vfft_shape"],
# #                 result.result_info["vfft_dtype"],
# #             )
# #             # sum_json = df_to_json(result.sum)
# #             detected_peaks = json.dumps(peaks_output(result.fitted))

# #             # send basic info
# #             await websocket.send_json({
# #                 "result_info": result.result_info,
# #                 "frame_number": result.result_info["frame_number"]
# #             })

# #             # send image data separately to client memory issues
# #             await websocket.send_json({"raw": raw,})
# #             await websocket.send_json({"fitted": detected_peaks})
# #             await websocket.send_json({"vfft": vfft})
# #             await websocket.send_json({"ifft": ifft})
# #             await asyncio.sleep(0.1)  # Sending 10 new images every second
# #     except Exception as e:
# #         print("Error:", e)
# #     finally:
# #         await websocket.close()


# if __name__ == "__main__":
#     import uvicorn

#     uvicorn.run(
#         "tr_ap_xps.publisher.ws_server:app", host="0.0.0.0", port=8001, reload=True
# )
