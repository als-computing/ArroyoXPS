import queue
from queue import Queue

from .processor import Result

raw_message_queue = queue.Queue()
processed_message_queue: Queue[Result] = Queue()