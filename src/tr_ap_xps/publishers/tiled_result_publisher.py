import asyncio
from dataclasses import dataclass
from typing import Union

from arroyo.publisher import Publisher
import numpy as np
import pandas as pd

from tiled.client.array import ArrayClient
from tiled.client.dataframe import DataFrameClient
from tiled.client.node import Container
from tiled.structures.array import ArrayStructure
from tiled.structures.data_source import DataSource
from tiled.structures.table import TableStructure


from ..config import settings
from ..schemas import XPSResult, XPSStart, XPSResultStop

app_settings = settings.xps

@dataclass
class TiledScan:
    run_node: ArrayClient
    integrated_frames: ArrayClient = None
    detected_peaks: DataFrameClient = None
    vfft: ArrayClient = None
    ifft: ArrayClient = None
    sum: ArrayClient = None
    timing: DataFrameClient = None



class TiledPublisher(Publisher[XPSResult | XPSStart | XPSResultStop]):
    current_tiled_scan: TiledScan = None # cache the data clients so each frame doesn't request them

    def __init__(self, runs_node: Container) -> None:
        super().__init__()
        self.runs_node = runs_node

    async def publish(self, message: Union[XPSResult | XPSStart | XPSResultStop]) -> None:
        if isinstance(message, XPSStart):
            self.current_tiled_scan_node = await asyncio.to_thread(
                                create_run_container,
                                self.runs_node,
                                message.scan_name)
            self.current_tiled_scan = TiledScan(run_node=self.current_tiled_scan_node)
            return

        elif isinstance(message, XPSResultStop):
            asyncio.to_thread(
                patch_tiled_array,
                self.current_tiled_scan_node.timing,
                message.function_timings,
                frame_num)
            return

        elif not isinstance(message, XPSResult):    
            raise KeyError(f"Unsupported message type {type(message)}")

        frame_num = message.frame_number

        if self.current_tiled_scan.integrated_frames is None:
            await asyncio.to_thread(
                create_data_nodes,
                self.current_tiled_scan_node,
                self.current_tiled_scan,
                message)
            return

        await asyncio.to_thread(
            patch_tiled_array,
            self.current_tiled_scan.integrated_frames,
            message.integrated_frames.array)
        
        await asyncio.to_thread(
            patch_tiled_dataframe,
            self.current_tiled_scan.detected_peaks,
            message.detected_peaks)
        
        await asyncio.to_thread(
            patch_tiled_array,
            self.current_tiled_scan.vfft,
            message.vfft.array)
        
        await asyncio.to_thread(
            patch_tiled_array,
            self.current_tiled_scan.ifft,
            message.ifft.array)
        
        await asyncio.to_thread(
            patch_tiled_array,
            self.current_tiled_scan.sum,
            message.sum.array)

def create_run_container(client: Container, name: str) -> Container:
    if name not in client:
        return client.create_container(name)
    return client[name]


def create_data_nodes(scan_node: Container,  tiled_scan: TiledScan, message: XPSResult) -> None:

    tiled_scan.integrated_frames = scan_node.write_array(message.integrated_frames.array, key="integrated_frames")
    tiled_scan.vfft = scan_node.write_array(message.vfft.array, key="vfft")
    tiled_scan.ifft = scan_node.write_array(message.ifft.array, key="ifft")
    tiled_scan.sum = scan_node.write_array(message.sum.array, key="sum")

    structure = TableStructure.from_pandas(message.detected_peaks.df)
    tiled_scan.detect = scan_node.new(
        "table",
        [
            DataSource(
                structure_family="table",
                structure=structure,
                mimetype="text/csv",
            ),
        ],
        key="detected_peaks",
    )

def patch_tiled_array(
        array_client: ArrayClient,
        array: np.ndarray,
        axis_to_increment: int = 0) -> None:
    
    # Apologies to developer from the future. This is confusing.
    # Every time we get an array, it's an shape (1, N) where N is the width
    # of the detector. Each array is integrated over the height of the detector.
    # Our job here is to add a new line to the array at the bottom.
    # This means we slice the array we're given, and add it to the bottom
    # so that we don't store copies that grow in size each time.

    shape = array_client.shape
    offset = (shape[axis_to_increment] + 1, )
    array_client.patch(array[-1: ], offset=offset, extend=True)   

def patch_tiled_dataframe(dataframe_client: DataFrameClient, df: pd.DataFrame) -> None:
    pass



#    def _create_runs_container(self, tiled_node, name: str):
#         return tiled_node.create_container(name)

#     def create_tiled_table_node(
#         self, parent_node: Node, data_frame: pd.DataFrame, name: str
#     ):
#         if name not in parent_node:
#             structure = TableStructure.from_pandas(data_frame)
#             frame = parent_node.new(
#                 "table",
#                 [
#                     DataSource(
#                         structure_family="table",
#                         structure=structure,
#                         mimetype="text/csv",
#                     ),
#                 ],
#                 key=name,
#             )
#             frame.write(data_frame)
#             return frame
#         parent_node[name].append_partition(data_frame, 0)
#         return parent_node[name]


#    @timer
#     def _tiled_update_lines_raw(self, new_integrated_df: pd.DataFrame):
#         if "lines_raw" not in self.tiled_nodes.run_node:
#             self.tiled_nodes.lines_raw_node = self.create_tiled_table_node(
#                 self.tiled_nodes.run_node, new_integrated_df, "lines_raw"
#             )
#         else:
#             self.tiled_nodes.lines_raw_node.append_partition(new_integrated_df, 0)