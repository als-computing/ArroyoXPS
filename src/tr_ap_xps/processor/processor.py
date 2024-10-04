import functools
import logging
import time

import numpy as np
import pandas as pd

from ..model import Event
from .pipeline.fft import calculate_fft_items
from .pipeline.peak_fitting import peak_fit
from .shared_queue import Result

# from ..tiled import create_array_node, create_table_node

# from tiled.structures.data_source import DataSource
# from tiled.structures.table import TableStructure


logger = logging.getLogger("tr-ap-xps.writer")


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


class XPSProcessor:
    def __init__(
        self,
        run_id: str,
        frames_per_cycle: int,
    ):
        self.run_id = run_id
        self.frames_per_cycle = frames_per_cycle
        self.integrated_frames_df: pd.DataFrame = None
        self.last_result: Result = None
        self.detected_peaks: pd.DataFrame = None
        self.vfft: pd.DataFrame = None
        self.ifft: pd.DataFrame = None
        self.sum: pd.DataFrame = None

    def _create_runs_container(self, tiled_node, name: str):
        return tiled_node.create_container(name)

    def _create_column_names(self, new_integrated_frame: np.array):
        return [str(i) for i in range(0, len(new_integrated_frame))]

    @timer
    def _compute_mean(self, curr_frame: np.array):
        return np.mean(curr_frame, axis=0)

    def _create_dataframe(
        self, frame_number: int, new_integrated_frame: np.array, column_names
    ):
        # data = np.concatenate(([frame_number], new_integrated_frame))
        data = np.insert(new_integrated_frame, 0, frame_number)
        df = pd.DataFrame([data], columns=["frame_number"] + column_names)
        df["frame_number"] = df["frame_number"].astype(int)
        return df

    @timer
    def _pd_to_np(self, frames_df: pd.DataFrame):
        return frames_df.iloc[:, 1:].to_numpy()

    @timer
    def _fit_peak(self, integrated_frame: np.ndarray):
        return peak_fit(integrated_frame)

    @timer
    def _integrated_frames_pd_to_np(self, integrated_frames_df: pd.DataFrame):
        return integrated_frames_df.iloc[:, 1:].to_numpy()

    @timer
    def _calculate_fft_items(nd_array: np.array, repeat_factor: int, width: int):
        return calculate_fft_items(nd_array, repeat_factor, width)

    def process_frame(self, event: Event):
        # Compute horizontally-integrated frame
        new_integrated_frame = self._compute_mean(event.image)

        # Column names for the dataframes
        frame_number = event.frame_num
        column_names = self._create_column_names(new_integrated_frame)
        new_integrated_df = self._create_dataframe(
            frame_number, new_integrated_frame, column_names
        )

        # Update the local cached dataframes
        self.integrated_frames_df = (
            pd.concat(  # curr + all the prev stacked avg frame -> fft
                [self.integrated_frames_df, new_integrated_df],
                ignore_index=True,
            )
        )

        # Things to do every so often
        if frame_number % self.frames_per_cycle == 0:
            self.integrated_frames_np = self._integrated_frames_pd_to_np(
                self.integrated_frames_df
            )
            # TODO: allow user to select repeat factor and width on UI
            vfft_np, sum_np, ifft_np = calculate_fft_items(
                self.integrated_frames_np, repeat_factor=20, width=0
            )
            detected_peaks_df = self._fit_peak(new_integrated_frame)
            result = Result(
                frame_number,
                self.integrated_frames_np,
                detected_peaks_df,
                vfft_np,
                ifft_np,
                sum_np,
            )
            self.last_result = result
            return result
            # TODO add tiled persistence later
            # self._tiled_update_lines_raw(new_integrated_df)
            # self.detected_peaks
            # TODO: update
        timer.end_frame()
        return None

    def finish(self, stop_data: dict):
        try:
            logger.info("finishing")
            # create_table_node(
            #     self.run_node, timer.timing_dataframe, "timer"
            # )

            # create_array_node(
            #       self.run_node, self.last_result.integrated_frame, "integrated_frame"
            # )

            # create_array_node(
            #       self.run_node, self.last_result.ifft, "ifft"
            # )

            # create_array_node(
            #       self.run_node, self.last_result.vfft, "vfft"
            # )

            # create_table_node(
            #       self.run_node, self.last_result.detected_peaks, "detected_peaks"
            # )

        finally:
            timer.reset()
