from tr_ap_xps.tiled import XPSDataSet


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
