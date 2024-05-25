import functools
import logging
import time

import numpy as np
import pandas as pd
from tiled.client import node
from tiled.structures.data_source import DataSource
from tiled.structures.table import TableStructure

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

    def get_timing_dataframe(self):
        return pd.DataFrame(self.accumulated_timings)

    def reset(self):
        self.accumulated_timings = []
        self.frame_timings = {}


# Create a global instance of the TimingDecorator
timer = TimingDecorator()


class XPSDataSet:
    def __init__(self, runs_node: node, run_id: str):
        self.run_id = run_id
        self.runs_node = runs_node
        self.run_node = self._create_runs_container(runs_node, run_id)
        self.lines_raw_node: node = None
        self.lines_filtered_node: node = None
        self.timing_node: node = None
        self.integrated_frames: pd.DataFrame = None
        self.integrated_filtered_frames: pd.DataFrame = None

    def _create_runs_container(self, tiled_node, name: str):
        return tiled_node.create_container(name)

    def create_tiled_table_node(
        self, parent_node: node, data_frame: pd.DataFrame, name: str
    ):
        if name not in parent_node:
            structure = TableStructure.from_pandas(data_frame)
            frame = parent_node.new(
                "table",
                [
                    DataSource(
                        structure_family="table",
                        structure=structure,
                        mimetype="text/csv",
                    ),
                ],
                key=name,
            )
            frame.write(data_frame)
            return frame
        parent_node[name].append_partition(data_frame, 0)
        return parent_node[name]

    @timer
    def _compute_mean(self, curr_frame: np.array):
        return np.mean(curr_frame, axis=0)

    def _create_column_names(self, new_integrated_frame: np.array):
        return [str(i) for i in range(0, len(new_integrated_frame))]

    def _create_dataframe(self, new_integrated_frame: np.array, column_names):
        return pd.DataFrame([new_integrated_frame], columns=column_names)

    @timer
    def _tiled_update_lines_raw(self, new_integrated_df: pd.DataFrame):
        if "lines_raw" not in self.run_node:
            self.lines_raw_node = self.create_tiled_table_node(
                self.run_node, new_integrated_df, "lines_raw"
            )
        else:
            self.lines_raw_node.append_partition(new_integrated_df, 0)

    @timer
    def _tiled_update_lines_filtered(self, new_integrated_df: pd.DataFrame):
        if "lines_filtered" not in self.run_node:
            self.lines_filtered_node = self.create_tiled_table_node(
                self.run_node, new_integrated_df, "lines_filtered"
            )
        else:
            self.lines_filtered_node.append_partition(new_integrated_df, 0)

    def new_integrated_frame(self, curr_frame: np.array):
        # Compute horizontally-integrated frame
        new_integrated_frame = self._compute_mean(curr_frame)
        # Column names for the dataframes
        column_names = self._create_column_names(new_integrated_frame)
        new_integrated_df = self._create_dataframe(new_integrated_frame, column_names)
        self._tiled_update_lines_raw(new_integrated_df)

        # Compute filtered integrated frames
        new_filtered_frame = (
            new_integrated_frame  # placeholder, until we have filtering code
        )
        new_integrated_df = self._create_dataframe(new_filtered_frame, column_names)
        self._tiled_update_lines_filtered(new_integrated_df)
        timer.end_frame()

    def finish(self):
        try:
            self.timing_node = self.create_tiled_table_node(
                self.run_node, timer.get_timing_dataframe(), "timer"
            )
            logger.info(timer.get_timing_dataframe())
        finally:
            timer.reset()
