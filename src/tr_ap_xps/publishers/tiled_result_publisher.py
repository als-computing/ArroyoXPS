import asyncio
import logging
from dataclasses import dataclass
from typing import Union

import numpy as np
import pandas as pd
from arroyo.publisher import Publisher
from tiled.client.array import ArrayClient
from tiled.client.dataframe import DataFrameClient
from tiled.client.node import Container
from tiled.structures.data_source import DataSource
from tiled.structures.table import TableStructure

from ..config import settings
from ..schemas import XPSResult, XPSResultStop, XPSStart

app_settings = settings.xps

logger = logging.getLogger(__name__)


@dataclass
class TiledScan:
    run_node: ArrayClient
    integrated_frames: ArrayClient = None
    detected_peaks: DataFrameClient = None
    vfft: ArrayClient = None
    ifft: ArrayClient = None
    sum: ArrayClient = None
    function_timings: DataFrameClient = None


class TiledPublisher(Publisher[XPSResult | XPSStart | XPSResultStop]):
    current_tiled_scan: TiledScan = (
        None  # cache the data clients so each frame doesn't request them
    )

    def __init__(self, runs_node: Container) -> None:
        super().__init__()
        self.runs_node = runs_node

    async def publish(
        self, message: Union[XPSResult | XPSStart | XPSResultStop]
    ) -> None:
        if isinstance(message, XPSStart):
            logger.info("  start")
            current_tiled_run_node = await asyncio.to_thread(
                create_run_container, self.runs_node, message.scan_name
            )
            self.current_tiled_scan = TiledScan(run_node=current_tiled_run_node)
            return

        elif isinstance(message, XPSResultStop):
            if not self.current_tiled_scan:
                return
            await asyncio.to_thread(
                create_tiled_table_node,
                self.current_tiled_scan.run_node,
                message.function_timings.df,
                "function_timings",
            )
            return

        elif not isinstance(message, XPSResult):
            raise KeyError(f"Unsupported message type {type(message)}")

        # First frame, create data nodes. Has to be now to get the shapes

        if self.current_tiled_scan.integrated_frames is None:
            await asyncio.to_thread(create_data_nodes, self.current_tiled_scan, message)
            return

        await asyncio.to_thread(self.update_tiled_scan, message)

        # await asyncio.to_thread(
        #     patch_tiled_array,
        #     self.current_tiled_scan.integrated_frames,
        #     message.integrated_frames.array)

        # await asyncio.to_thread(
        #     patch_tiled_dataframe,
        #     self.current_tiled_scan.detected_peaks,
        #     message.detected_peaks)

        # await asyncio.to_thread(
        #     patch_tiled_array,
        #     self.current_tiled_scan.vfft,
        #     message.vfft.array)

        # await asyncio.to_thread(
        #     patch_tiled_array,
        #     self.current_tiled_scan.ifft,
        #     message.ifft.array)

        # await asyncio.to_thread(
        #     patch_tiled_array,
        #     self.current_tiled_scan.sum,
        #     message.sum.array)

    def update_tiled_scan(self, message: XPSResult) -> None:
        patch_tiled_array(
            self.current_tiled_scan.integrated_frames, message.integrated_frames.array
        )
        patch_tiled_array(self.current_tiled_scan.vfft, message.vfft.array)
        patch_tiled_array(self.current_tiled_scan.ifft, message.ifft.array)
        patch_tiled_array(self.current_tiled_scan.sum, message.sum.array)
        append_table_node(
            self.current_tiled_scan.detected_peaks, message.detected_peaks.df
        )


def create_run_container(client: Container, name: str) -> Container:
    if name not in client:
        return client.create_container(name)
    return client[name]


def create_data_nodes(tiled_scan: TiledScan, message: XPSResult) -> None:
    tiled_scan.integrated_frames = tiled_scan.run_node.write_array(
        message.integrated_frames.array, key="integrated_frames"
    )
    tiled_scan.vfft = tiled_scan.run_node.write_array(message.vfft.array, key="vfft")
    tiled_scan.ifft = tiled_scan.run_node.write_array(message.ifft.array, key="ifft")
    tiled_scan.sum = tiled_scan.run_node.write_array(message.sum.array, key="sum")
    tiled_scan.detected_peaks = create_tiled_table_node(
        tiled_scan.run_node, message.detected_peaks.df, "detected_peaks"
    )


def patch_tiled_array(
    array_client: ArrayClient, array: np.ndarray, axis_to_increment: int = 0
) -> None:
    # Apologies to developer from the future. This is confusing.
    # Every time we get an array, it's an shape (1, N) where N is the width
    # of the detector. Each array is integrated over the height of the detector.
    # Our job here is to add a new line to the array at the bottom.
    # This means we slice the array we're given, and add it to the bottom
    # so that we don't store copies that grow in size each time.

    shape = array_client.shape
    offset = (shape[axis_to_increment] + 1,)
    array_client.patch(array[-1:], offset=offset, extend=True)


def create_tiled_table_node(
    parent_node: Container, data_frame: pd.DataFrame, name: str
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


def append_table_node(table_node: DataFrameClient, data_frame: pd.DataFrame):
    table_node.append_partition(data_frame, 0)
