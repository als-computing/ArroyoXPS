import os
from pprint import pprint

import numpy as np
from tiled.client import from_uri

c = from_uri(
    "http://localhost:8000/api", api_key=os.getenv("TILED_SINGLE_USER_API_KEY")
)
array = np.array([[[1, 2], [3, 4]]])

array_node = c.write_array(array, key="test4")

block = np.array([[[5, 6], [7, 8]]])

pprint(array_node.__dict__)
array_node.write_block(block, block=(1, 0, 0))
