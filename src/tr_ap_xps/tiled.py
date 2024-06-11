import numpy as np
import pandas as pd
from tiled.client.node import Node


def create_array_node(
    parent_node: Node, arr: np.ndarray, name: str, metadata: dict = {}
):
    parent_node.write_array(arr, key=name, metadata=metadata)


def create_table_node(
    parent_node: Node, df: pd.DataFrame, name: str, metadata: dict = {}
):
    parent_node.write_dataframe(df, key=name, metadata=metadata)
