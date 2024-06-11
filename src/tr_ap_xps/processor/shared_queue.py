import queue
from queue import Queue

from ..model import Result

raw_message_queue = queue.Queue()
processed_message_queue: Queue[Result] = Queue()
