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
    def __init__(self, zarr_location: str, run_name: str) -> None:
        # Create or open a Zarr array with the ability to resize
        self.store = zarr.DirectoryStore(zarr_location.join(run_name))
        self.run_group = zarr.group(self.store)

    # Function to append a 2D chunk to the 3D array along the z-axis
    def append_1d_chunk(self, group_name: str, chunk_1d: np.array, axis=0):
        # Check if the array already exists
        if group_name in self.run_group:
            self.zarr_array = self.run_group[group_name]
        else:
            self.zarr_array = self.run_group.empty(
                group_name, shape=(0, 10), chunks=(10, 10), dtype=chunk_1d.dtype
            )
        # Current shape of the Zarr array
        shape = list(self.zarr_array.shape)

        # Determine the new shape after appending the 2D chunk
        new_shape = shape[:]
        new_shape[axis] += 1

        # Resize the Zarr array to accommodate the new chunk
        self.zarr_array.resize(tuple(new_shape))

        # Determine the slice to insert the new chunk
        slice_obj = [slice(None)] * len(shape)
        slice_obj[axis] = shape[axis]

        # Insert the new chunk
        self.zarr_array[tuple(slice_obj)] = chunk_1d
