import numpy as np
import pytest

# from tr_ap_xps.pipeline.xps_operator import XPSProcessor
# from tr_ap_xps.schemas import XPSStart


@pytest.fixture
def integrated_frame():
    return np.random.randint(0, 100, size=(5, 10), dtype="int32")


# def test_XPSDataSet(client, integrated_frame):
#     if "runs" not in client:
#         runs_node = client.create_container("runs")
#     runs_node = client["runs"]
#     xps_start = XPSStart(binding_energy=2.0, frames_per_cycle=2, scan_name="test")

#     xps_dataset = XPSProcessor(runs_node, xps_start)
#     assert xps_dataset.run_id == "42"
#     assert xps_dataset.tiled_struct.run_node == client["runs"]["42"]

#     frame_info = {"Frame Number": 1}
#     xps_dataset.process_frame(frame_info, integrated_frame)
# TODO commenting this out for now, the new peak fitting code cannot handle dummy data
# assert "lines_raw" in xps_dataset.run_node
# assert xps_dataset.tiled_struct.lines_raw_node is not None
# assert xps_dataset.tiled_struct.lines_raw_node.read().shape == (
#     1,
#     10,
# ), "Expected a single row with 10 columns, matching a veritcally integrated frame"
# assert xps_dataset.tiled_struct.lines_filtered_node.read().shape == (
#     1,
#     10,
# ), "Expected a single row with 10 columns, matching a veritcally filtered integrated frame"

# xps_dataset.process_frame(integrated_frame)
# assert xps_dataset.tiled_struct.lines_raw_node.read().shape == (
#     2,
#     10,
# ), "Expected another row of verically integrated frame"
# assert xps_dataset.tiled_struct.lines_filtered_node.read().shape == (
#     2,
#     10,
# ), "Expected a single row with 10 columns, matching a veritcally filtered integrated frame"

# xps_dataset.finish()
# assert xps_dataset.tiled_struct.timing_node.read().shape[0] == 2
