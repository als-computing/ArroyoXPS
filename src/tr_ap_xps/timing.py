import functools
import time

import pandas as pd


class TimingDecorator:
    def __init__(self):
        self.accumulated_timings = []
        self.frame_timings = {}

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            duration = end_time - start_time
            self.frame_timings[func.__name__] = duration
            # print(f"{func.__name__} took {duration:.4f} seconds")
            return result

        return wrapper

    def end_frame(self):
        if self.frame_timings:
            self.accumulated_timings.append(self.frame_timings)
        self.frame_timings = {}

    @property
    def timing_dataframe(self):
        return pd.DataFrame(self.accumulated_timings)

    def reset(self):
        self.accumulated_timings = []
        self.frame_timings = {}


# Create a global instance of the TimingDecorator
timer = TimingDecorator()
