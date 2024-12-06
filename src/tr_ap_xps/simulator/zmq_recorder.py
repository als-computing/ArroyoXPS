import json
import logging
import pickle
from pathlib import Path

import typer
import zmq

from ..log_utils import setup_logger

logger = logging.getLogger(__name__)


def main(
    # zmq_pub_address: str = "tcp://192.168.1.84",
    zmq_pub_address: str = "tcp://131.243.75.240",
    zmq_pub_port: int = 5555,
    zme_hwm: int = 5000,
    scan_name="scan4",
    data_dir="./sample_data",
    log_level="debug",
):
    setup_logger(logger, log_level)

    logger.info(f"zmq_pub_address: {zmq_pub_address}")
    logger.info(f"zmq_pub_port: {zmq_pub_port}")
    # set connection
    ctx = zmq.Context()
    socket = ctx.socket(zmq.SUB)
    logger.info(f"binding to: {zmq_pub_address}:{zmq_pub_port}")
    socket.connect(f"{zmq_pub_address}:{zmq_pub_port}")
    socket.setsockopt(zmq.SUBSCRIBE, b"")
    socket.set_hwm(zme_hwm)
    msg_index = 0
    scan_dir = Path(data_dir) / scan_name
    scan_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Writing to {scan_dir}")
    while True:
        msg = socket.recv()
        logger.info(f"msg # {msg_index}")
        # logger.info(msg)
        print_json(msg)
        scan_file = scan_dir / Path(str(msg_index) + ".pickle")
        with open(scan_file, "ab") as msg_file:
            pickle.dump(msg, msg_file)

        msg_index += 1
        # if logger.isEnabledFor(logging.DEBUG):
        #     logger.debug(msg)


def print_json(msg: bytes) -> None:
    try:
        json_dict = json.loads(msg.decode("utf-8"))
        print(json.dumps(json_dict, indent=4))
    except Exception:
        print("frame")


if __name__ == "__main__":
    typer.run(main)
