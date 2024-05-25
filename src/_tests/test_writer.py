import numpy as np
import pytest

from tr_ap_xps.writer import XPSDataSet


@pytest.fixture
def integrated_frame():
    return np.random.randint(0, 100, size=(5, 10), dtype="int32")


def test_XPSDataSet_init(client, integrated_frame):
    if "runs" not in client:
        runs_node = client.create_container("runs")
    runs_node = client["runs"]
    xps_dataset = XPSDataSet(runs_node, "42")
    assert xps_dataset.run_id == "42"
    assert xps_dataset.run_node == client["runs"]["42"]

    xps_dataset.new_integrated_frame(integrated_frame)
    assert "lines_raw" in xps_dataset.run_node
    assert xps_dataset.lines_raw_node is not None
    assert xps_dataset.lines_raw_node.read().shape == (
        1,
        10,
    ), "Expected a single row with 10 columns, matching a veritcally integrated frame"

    xps_dataset.new_integrated_frame(integrated_frame)
    assert xps_dataset.lines_raw_node.read().shape == (
        2,
        10,
    ), "Expected another row of verically integrated frame"
