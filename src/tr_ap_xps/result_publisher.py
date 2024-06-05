import zmq

from tr_ap_xps.processor import Result


class XPSResultPublisher:
    def __init__(
        self, zmq_pub_address: str = "tcp://127.0.0.1", zmq_pub_port: int = 5559
    ):
        self.ctx = zmq.Context()
        self.socket = self.ctx.socket(zmq.PUB)
        self.socket.bind(f"{zmq_pub_address}:{zmq_pub_port}")

    def send_result(self, result: Result):
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
        # self.socket.send(result.detected_peaks)
        self.socket.send(result.vfft)
        self.socket.send(result.ifft)
        self.socket.send(result.sum)
