# This file is for debugging purposes only. Not part of the regular workflow.

import os
import threading

import dotenv

# import matplotlib.pyplot as plt
import numpy as np
import zmq
from tiled.client import from_uri

# from tr_ap_xps.cli import listen
from tr_ap_xps.processor import Result

dotenv.load_dotenv()

client = from_uri(
    "http://localhost:8000/api", api_key=os.getenv("TILED_SINGLE_USER_API_KEY")
)
if client.get("runs") is None:
    client.create_container("runs")


def got_a_result(result):
    print(result)
    # plt.imshow(result.integrated_frame)
    # plt.show()


def listen():
    while True:
        try:
            print("!!!!!!")
            result_info = socket.recv_json()
            print(result_info)
            integrated_frame = socket.recv()
            print(len(integrated_frame))
            # detected_peaks = socket.recv()
            vfft = socket.recv()
            ifft = socket.recv()
            sum_buff = socket.recv()
            shape = result_info["shape"]
            print(f"{tuple(shape)=}")
            integrated_frame_np = np.frombuffer(
                integrated_frame, dtype=result_info["dtype"]
            ).reshape(tuple(shape))
            detect_peaks_df = None  # serialize a dataframe from buffer?
            vfft_np = np.frombuffer(vfft, dtype=result_info["vfft_dtype"]).reshape(
                tuple(result_info["vfft_shape"])
            )
            print(2)
            ifft_np = np.frombuffer(ifft, dtype=result_info["ifft_dtype"]).reshape(
                tuple(result_info["ifft_shape"])
            )
            print(3)
            sum_np = np.frombuffer(sum_buff, dtype=result_info["sum_dtype"]).reshape(
                tuple(result_info["sum_shape"])
            )
            print(4)
            got_a_result(
                Result(
                    result_info["frame_number"],
                    integrated_frame_np,
                    detect_peaks_df,
                    vfft_np,
                    ifft_np,
                    sum_np,
                )
            )
        except Exception as e:
            print(e)


# class Result:
#     frame_number: int
#     integrated_frame: np.ndarray
#     detected_peaks: pd.DataFrame
#     vfft: np.ndarray
#     ifft: np.ndarray
#     sum: np.ndarray


ctx = zmq.Context()
socket = ctx.socket(zmq.SUB)
socket.connect("tcp://127.0.0.1:5559")
socket.setsockopt(zmq.SUBSCRIBE, b"")

# Create and start a new thread for the listen function
listen_thread = threading.Thread(target=listen)
listen_thread.start()
