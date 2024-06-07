import io
import logging
import queue
import threading

import zmq

from .shared_queue import processed_message_queue

logger = logging.getLogger(__name__)


class XPSResultPublisher:
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
        logger.info("XPSResultPublisher started")
        while True:
            try:
                result = None
                try:
                    # result = await asyncio.to_thread(processed_message_queue.get, timeout=1)
                    result = processed_message_queue.get(timeout=1)
                except queue.Empty:
                    pass
                if result is None:
                    continue
                self.socket.send_json(
                    {
                        "frame_number": result.frame_number,
                        "shape": result.integrated_frame.shape,
                        "dtype": str(result.integrated_frame.dtype),
                        "vfft_dtype": str(result.vfft.dtype),
                        "vfft_shape": result.vfft.shape,
                        "ifft_dtype": str(result.ifft.dtype),
                        "ifft_shape": result.ifft.shape,
                        "sum_dtype": str(result.sum.dtype),
                        "sum_shape": result.sum.shape,
                    }
                )  # Convert dtype to string
                self.socket.send(result.integrated_frame)
                peaks_buffer = io.StringIO()
                result.detected_peaks.to_csv(peaks_buffer, index=False)
                self.socket.send_string(peaks_buffer.getvalue())
                self.socket.send(result.vfft)
                self.socket.send(result.ifft)
                self.socket.send(result.sum)
            except Exception as e:
                logger.exception(e)
