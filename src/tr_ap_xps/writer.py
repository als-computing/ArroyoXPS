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


# class ZarrResultStore:
#     # so experiemental that it barely works
#     def __init__(self, zarr_location: str, run_name: str, frame_shape: tuple, dtype=np.dtype) -> None:
#         self.frame_shape = frame_shape

#         # Create or open a Zarr array with the ability to resize
#         self.store = zarr.DirectoryStore(zarr_location.join(run_name))
#         self.run_group = zarr.group(self.store)

#         # Create a group to store the results
#         if "results" not in self.run_group:
#             self.results_group = self.run_group.create_group("results")
#         self.results_group = self.run_group["results"]

#         shape_3d = (0, *frame_shape)

#         # # Create a dataset to store a 2D array, height will be number of frames, width same as frame width
#         self.v_integrated_frame_dataset = self._get_or_create_dataset(
#             self.results_group, "v_integrated_frame", (0, self.frame_shape[1]), np.float64,
#         )
#         self.vfft_dataset = self._get_or_create_dataset(
#             self.results_group, "vfft", (0, 0, frame_shape[1]), np.float64
#         )
#         self.ifft_dataset = self._get_or_create_dataset(
#             self.results_group, "ifft", shape_3d, np.float64
#         )
#         self.sum_data_dataset = self._get_or_create_dataset(
#             self.results_group, "sum_data", shape_3d, np.float64
#         )

#     def _get_or_create_dataset(
#         self, group, dataset_name: str, shape: tuple, dtype: np.dtype
#     ):
#         # Create the shape and maxshape dynamically based on dims
#         maxshape = (None,) * len(shape)
#         # Check if the array already exists
#         if dataset_name not in group:
#             return group.create_dataset(
#                 dataset_name,
#                 shape=shape,
#                 dtype=dtype,
#                 chunks=True,
#                 maxshape=maxshape,
#             )
#         return group[dataset_name]

#     def new_integrated_frame(self, curr_frame: np.array):
#         # Every time a new frame comes in, we will:
#         #  1. Integrate the frame along the vertical axis
#         #  2. Append the integrated frame to the raw dataset
#         #  3. Append the filtered (vfft, filter, ifft) frame to the result dataset
#         #  . Fit the filtered image and append the fitted peak to the trending dataset
#         assert curr_frame.shape == self.frame_shape,
# f"Frame width does not match. {self.frame_shape=}, {curr_frame.shape=}"
#         new_integrated_frame = np.mean(curr_frame, axis=0)
#         self.append_1d_chunk(self.v_integrated_frame_dataset, new_integrated_frame)

#         vfft = get_vfft(self.v_integrated_frame_dataset)
#         self.append_2d_chunk(self.vfft_dataset, vfft)

#     # Function to append a 1D chunk to the 3D array along the z-axis
#     def append_1d_chunk(self, dataset, chunk_1d: np.array, axis=0):
#         assert (
#             len(chunk_1d) == self.frame_shape[1]
#         ), f"Chunk length does not match the frame width. {self.frame_shape=}, {len(chunk_1d)=}"
#         # Current shape of the Zarr array
#         shape = list(dataset.shape)

#         # Determine the new shape after appending the 2D chunk
#         new_shape = shape[:]
#         new_shape[axis] += 1

#         # Resize the Zarr array to accommodate the new chunk
#         dataset.resize(tuple(new_shape))

#         # Determine the slice to insert the new chunk
#         slice_obj = [slice(None)] * len(shape)
#         slice_obj[axis] = shape[axis]

#         # Insert the new chunk
#         dataset[tuple(slice_obj)] = chunk_1d

#     # Function to append a 2d chunk to the 3D array along the z-axis
#     def append_2d_chunk(self, dataset, chunk_2d: np.array, axis=0):
#         assert (
#             chunk_2d.shape == self.frame_shape
#         ), f"Chunk length does not match the frame width. {self.frame_shape=}, {chunk_2d.shape=}"
#         # Current shape of the Zarr array
#         shape = list(dataset.shape)

#         # Determine the new shape after appending the 2D chunk
#         new_shape = shape[:]
#         new_shape[axis] += 1

#         # Resize the Zarr array to accommodate the new chunk
#         dataset.resize(tuple(new_shape))

#         # Determine the slice to insert the new chunk
#         slice_obj = [slice(None)] * len(shape)
#         slice_obj[axis] = shape[axis]

#         # Insert the new chunk
#         dataset[tuple(slice_obj)] = chunk_2d
