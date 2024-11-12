import functools
import logging
import time
from dataclasses import dataclass

import numpy as np
import pandas as pd
from tiled.client.node import Node
from tiled.structures.data_source import DataSource
from tiled.structures.table import TableStructure

from .fft import calculate_fft_items
from .peak_fitting import peak_fit
from ..schemas import (
    DataFrameModel,
    NumpyArrayModel,
    XPSRawEvent,
    XPSResult,
    XPSStart)

# from ..tiled import create_array_node, create_table_node


logger = logging.getLogger("tr-ap-xps.processor")


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
    """
    A class to process XPS (X-ray Photoelectron Spectroscopy) data.

    """

    def __init__(self, message: XPSStart):
        self.frames_per_cycle = message.frames_per_cycle
        self.integrated_frames_df: pd.DataFrame = None
        self.integrated_filtered_frames_df: pd.DataFrame = None
        self.detected_peaks: pd.DataFrame = None
        self.vfft: pd.DataFrame = None
        self.ifft: pd.DataFrame = None
        self.sum: pd.DataFrame = None

 
    @timer
    def _compute_mean(self, curr_frame: np.array):
        return np.mean(curr_frame, axis=0)

    def _create_column_names(self, new_integrated_frame: np.array):
        return [str(i) for i in range(0, len(new_integrated_frame))]

    def _create_dataframe(
        self, frame_number: int, new_integrated_frame: np.array, column_names
    ):
        # data = np.concatenate(([frame_number], new_integrated_frame))
        data = np.insert(new_integrated_frame, 0, frame_number)
        df = pd.DataFrame([data], columns=["frame_number"] + column_names)
        df["frame_number"] = df["frame_number"].astype(int)
        return df

 

    # TODO: we do not have filtered, but 4 the other instead. So, update this part?
    @timer
    def _tiled_update_lines_filtered(self, new_integrated_df: pd.DataFrame):
        if "lines_filtered" not in self.tiled_nodes.run_node:
            self.tiled_nodes.lines_filtered_node = self.create_tiled_table_node(
                self.tiled_nodes.run_node, new_integrated_df, "lines_filtered"
            )
        else:
            self.tiled_nodes.lines_filtered_node.append_partition(new_integrated_df, 0)

    @timer
    def _integrated_frames_pd_to_np(self, integrated_frames_df: pd.DataFrame):
        return integrated_frames_df.iloc[:, 1:].to_numpy()

    @timer
    def _integrated_filtered_frames_pd_to_np(
        self, integrated_filtered_frames_df: pd.DataFrame
    ):
        return integrated_filtered_frames_df.iloc[:, 1:].to_numpy()


    # def process_frame(self, frame_info: dict, curr_frame: np.array):
    def process_frame(self, message: XPSRawEvent) -> None:
        # Compute horizontally-integrated frame
        new_integrated_frame = self._compute_mean(message.image.array)

        # Peak detection on new_integrated_frame
        detected_peaks_df = peak_fit(new_integrated_frame)

        # Compute filtered integrated frames
        new_filtered_frame = (
            new_integrated_frame  # placeholder, until we have filtering code
        )

        # Column names for the dataframes
        frame_number = message.image_info.frame_number
        column_names = self._create_column_names(new_integrated_frame)
        new_integrated_df = self._create_dataframe(
            frame_number, new_integrated_frame, column_names
        )
        new_filtered_df = self._create_dataframe(
            frame_number, new_filtered_frame, column_names
        )

        # Update the local cached dataframes
        self.integrated_frames_df = (
            pd.concat(  # curr + all the prev stacked avg frame -> fft
                [self.integrated_frames_df, new_integrated_df],
                ignore_index=True,
            )
        )

        # TODO:
        self.integrated_filtered_frames_df = pd.concat(
            [self.integrated_filtered_frames_df, new_filtered_df], ignore_index=True
        )

        # Things to do every so often
        if frame_number % self.frames_per_cycle == 0:
            integrated_frames_np = self._integrated_frames_pd_to_np(
                self.integrated_frames_df
            )
            # TODO: allow user to select repeat factor and width on UI
            vfft_np, sum_np, ifft_np = calculate_fft_items(
                integrated_frames_np, repeat_factor=20, width=0
            )

            result = XPSResult(
                frame_number=frame_number,
                integrated_frames=NumpyArrayModel(array=integrated_frames_np),
                detected_peaks=DataFrameModel(df=detected_peaks_df),
                vfft=NumpyArrayModel(array=vfft_np),
                ifft=NumpyArrayModel(array=ifft_np),
                sum=NumpyArrayModel(array=sum_np),
            )
            return result

        timer.end_frame()
