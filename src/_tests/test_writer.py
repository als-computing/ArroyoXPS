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


# def test_update_zarr(tmpdir):
#     # Test that the writer can append a 2D chunk to a 3D Zarr array
#     # Create a Zarr array
#     zarr_location = str(tmpdir.join("test.zarr"))
#     writer = ResultStore(zarr_location, "run42", (5, 10), np.int32)
#     assert zarr.open(zarr_location) is not None
#     assert writer.run_group is not None
#     assert writer.results_group is not None
#     assert writer.v_integrated_frame_dataset is not None
#     assert writer.vfft_dataset is not None
#     assert writer.ifft_dataset is not None
#     assert writer.sum_data_dataset is not None

#     # # Append a 1D chunk
#     # chunk_1d = np.random.rand(10).astype(np.int32)
#     # writer.append_1d_chunk(writer.vfft_dataset, chunk_1d)
#     # assert writer.vfft_dataset.shape == (1, 10)
#     # assert np.allclose(writer.vfft_dataset[0], chunk_1d)

#     new_frame = np.random.randint(0, 100, size=(5, 10), dtype='int32')
#     writer.new_integrated_frame(new_frame)
