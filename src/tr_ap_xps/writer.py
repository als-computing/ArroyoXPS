import numpy as np
import zarr
from tiled.client import node


class XPSDataSet:
    def __init__(self, runs_node: node, run_id: str):
        self.run_id = run_id
        self.runs_node = runs_node
        self.run_node = self._get_or_create_node(runs_node, run_id)
        self.raw_data_node = self._get_or_create_node(self.run_node, "raw_data")
        self.integrated_data_node = self._get_or_create_node(
            self.run_node, "integrated_data"
        )
        self.vfft_node = self._get_or_create_node(self.run_node, "vfft")
        self.ifft_node = self._get_or_create_node(self.run_node, "ifft")
        self.sum_data_node = self._get_or_create_node(self.run_node, "sum_data")
        self.trending_node = self._get_or_create_node(self.run_node, "trending")

    def _get_or_create_node(self, tiled_node, name: str):
        if name not in tiled_node:
            return tiled_node.create_container(name)
        return tiled_node[name]


class ResultWriter:
    def __init__(self, zarr_location: str, run_name: str, frame_width: int) -> None:
        self.frame_width = frame_width
        # Create or open a Zarr array with the ability to resize
        self.store = zarr.DirectoryStore(zarr_location.join(run_name))
        self.run_group = zarr.group(self.store)

        # Create a group to store the results
        if "results" not in self.run_group:
            self.results_group = self.run_group.create_group("results")
        self.results_group = self.run_group["results"]

        # Create the datasets to store the results
        self.v_integrated_frame_dataset = self._get_or_create_1d_dataset(
            self.results_group, "v_integrated_frame", self.frame_width, np.int32
        )
        self.vfft_dataset = self._get_or_create_1d_dataset(
            self.results_group, "vfft", self.frame_width, np.int32
        )
        self.ifft_dataset = self._get_or_create_1d_dataset(
            self.results_group, "ifft", self.frame_width, np.int32
        )
        self.sum_data_dataset = self._get_or_create_1d_dataset(
            self.results_group, "sum_data", self.frame_width, np.int32
        )

    def _get_or_create_1d_dataset(
        self, group, dataset_name: str, length: int, dtype: np.dtype
    ):
        # Check if the array already exists
        if dataset_name not in group:
            return group.create_dataset(
                dataset_name,
                shape=(0, length),
                dtype=dtype,
                chunks=True,
                maxshape=(None,),
            )
        return group[dataset_name]

    # Function to append a 1D chunk to the 3D array along the z-axis
    def append_1d_chunk(self, dataset, chunk_1d: np.array, axis=0):
        assert (
            len(chunk_1d) == self.frame_width
        ), f"Chunk length does not match the frame width. {self.frame_width=}, {len(chunk_1d)=}"
        # Current shape of the Zarr array
        shape = list(dataset.shape)

        # Determine the new shape after appending the 2D chunk
        new_shape = shape[:]
        new_shape[axis] += 1

        # Resize the Zarr array to accommodate the new chunk
        dataset.resize(tuple(new_shape))

        # Determine the slice to insert the new chunk
        slice_obj = [slice(None)] * len(shape)
        slice_obj[axis] = shape[axis]

        # Insert the new chunk
        dataset[tuple(slice_obj)] = chunk_1d
