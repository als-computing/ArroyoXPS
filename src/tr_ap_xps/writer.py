import numpy as np
import pandas as pd
from tiled.client import node
from tiled.structures.data_source import DataSource
from tiled.structures.table import TableStructure


class XPSDataSet:
    def __init__(self, runs_node: node, run_id: str):
        self.run_id = run_id
        self.runs_node = runs_node
        self.run_node = self._get_or_create_container(runs_node, run_id)
        self.lines_raw_node = None

    def _get_or_create_container(self, tiled_node, name: str):
        if name not in tiled_node:
            return tiled_node.create_container(name)
        return tiled_node[name]

    def _get_or_create_table(self, tiled_node, data_frame: pd.DataFrame, name: str):
        if name not in tiled_node:
            structure = TableStructure.from_pandas(data_frame)
            frame = tiled_node.new(
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
        tiled_node[name].append_partition(data_frame, 0)
        return tiled_node[name]

    def new_integrated_frame(self, curr_frame: np.array):
        new_integrated_frame = np.mean(curr_frame, axis=0)
        column_names = [str(i) for i in range(0, len(new_integrated_frame))]
        new_integrated_frame = pd.DataFrame(
            [new_integrated_frame], columns=column_names
        )
        self.lines_raw_node = self._get_or_create_table(
            self.run_node, new_integrated_frame, "lines_raw"
        )
