import logging
import queue
import threading

import zmq

from .shared_queue import processed_message_queue

logger = logging.getLogger("processor")


class XPSResultPublisher:
    """
    Publishes XPS results to a ZeroMQ socket.

    Parameters:
        zmq_pub_address (str): The ZeroMQ publisher address. Default is "tcp://127.0.0.1".
        zmq_pub_port (int): The ZeroMQ publisher port. Default is 5556.
    """

    def __init__(
        self, zmq_pub_address: str = "tcp://127.0.0.1", zmq_pub_port: int = 5556
    ):
        self.ctx = zmq.Context()
        self.socket = self.ctx.socket(zmq.PUB)
        self.socket.bind(f"{zmq_pub_address}:{zmq_pub_port}")
        self.thread = threading.Thread(target=self.listen, name="ResultPublisherThread")
        self.thread.daemon = True
        self.thread.start()

    def listen(self):
        """
        Listen for results and publish them.

        This method continuously listens for results from the `processed_message_queue`
        and publishes them to a ZMQ pub/sub socket. It sends various information about
        the result, such as frame number, shape, and data types, along with the actual
        result data.

        For each result, this produces this sends the following messages in order:
        - frame_info: json string with information about the frames that are coming
        - the detected peaks (JSON of the format:
            [ {"x": 235, "h": 433.3: "fwhm": 4334} ]
        - the integrated frame (CFormatted Buffer)
        - the vfft of the integrated frame (CFormatted Buffer)
        - the ifft of the intetrated frame ((CFormatted Buffer))

        """
        logger.info("XPSResultPublisher started")
        while True:
            try:
                result = None
                try:
                    result = processed_message_queue.get(timeout=1)
                except queue.Empty:
                    pass
                if result is None:
                    continue
                frame_info = {
                    "frame_number": result.frame_num,
                    "shape": result.integrated_frame.shape,
                    "dtype": str(result.integrated_frame.dtype),
                    "vfft_dtype": str(result.vfft.dtype),
                    "vfft_shape": result.vfft.shape,
                    "ifft_dtype": str(result.ifft.dtype),
                    "ifft_shape": result.ifft.shape,
                    "sum_dtype": str(result.sum.dtype),
                    "sum_shape": result.sum.shape,
                }
                self.socket.send_json(frame_info)
                self.socket.send(result.integrated_frame)
                peaks_json = result.detected_peaks.to_json(orient="split")
                self.socket.send_json(peaks_json)
                self.socket.send(result.vfft)
                self.socket.send(result.ifft)
                print(f"{frame_info=}")
            except Exception as e:
                logger.exception(e)
