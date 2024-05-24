import numpy as np
import zarr

from tr_ap_xps.writer import ResultWriter, XPSDataSet


def test_XPSDataSet_init(client):
    if "runs" not in client:
        runs_node = client.create_container("runs")
    runs_node = client["runs"]
    xps_dataset = XPSDataSet(runs_node, "42")
    assert xps_dataset.run_id == "42"
    assert xps_dataset.run_node == client["runs"]["42"]
    assert xps_dataset.raw_data_node == client["runs"]["42"]["raw_data"]
    assert xps_dataset.integrated_data_node == client["runs"]["42"]["integrated_data"]
    assert xps_dataset.vfft_node == client["runs"]["42"]["vfft"]
    assert xps_dataset.ifft_node == client["runs"]["42"]["ifft"]
    assert xps_dataset.sum_data_node == client["runs"]["42"]["sum_data"]
    assert xps_dataset.trending_node == client["runs"]["42"]["trending"]


def test_update_zarr(tmpdir):
    # Test that the writer can append a 2D chunk to a 3D Zarr array
    # Create a Zarr array
    zarr_location = str(tmpdir.join("test.zarr"))
    writer = ResultWriter(zarr_location, "run42")
    assert zarr.open(zarr_location) is not None
    # Append a 1D chunk
    chunk_1d = np.random.rand(10).astype(np.int32)
    writer.append_1d_chunk("fft", chunk_1d)
    assert writer.run_group["fft"].shape == (1, 10)
    assert np.allclose(writer.run_group["fft"][0], chunk_1d)
