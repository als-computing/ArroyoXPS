import numpy
from tiled.client import node


class XPSDataSet:
    def __init__(self, runs_node: node, run_id: str):
        self.run_id = run_id
        self.runs_node = runs_node
        self.run_node = self._get_or_create_node(runs_node, run_id)
        self.raw_data_node = self._get_or_create_node(
            self.run_node, "raw_data", array=True
        )
        self.integrated_data_node = self._get_or_create_node(
            self.run_node, "integrated_data"
        )
        self.vfft_node = self._get_or_create_node(self.run_node, "vfft")
        self.ifft_node = self._get_or_create_node(self.run_node, "ifft")
        self.sum_data_node = self._get_or_create_node(self.run_node, "sum_data")
        self.trending_node = self._get_or_create_node(self.run_node, "trending")

    def _get_or_create_node(self, tiled_node, name: str, array=False):
        if array:
            if name not in tiled_node:
                return tiled_node.write_array(numpy.array([4, 5, 6]), key=name)
            return tiled_node[name]

        if name not in tiled_node:
            return tiled_node.create_container(name)
        return tiled_node[name]


class XPSDataSetSeparate:
    def __init__(self, runs_node, run_id: str):
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
