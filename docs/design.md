# Design


## Experiment Monitoring
System design notes for supporting the [Experiment Monitoring](./user_strories.md#experiment-monitoring) user story.

### Sequence Diagram

```mermaid

sequenceDiagram
    actor user
    user ->> labview: start scan
    labview ->> ZMQImageDispatcher: start_scan(scan_metadata)
    ZMQImageDispatcher ->> XPSDataSet: create(scan_metadata)
    activate XPSDataSet
    XPSDataSet ->> Tiled: create run collection with metadata

    XPSDataSet ->> Tiled: create intgrated frame table
    XPSDataSet ->> Tiled: create filtered frame table
    deactivate XPSDataSet
    labview ->>+ ZMQImageDispatcher: send new frame

    activate XPSDataSet
    ZMQImageDispatcher ->> XPSDataSet: new frame
    XPSDataSet ->> XPSDataSet: vertically integrate frame
    XPSDataSet ->> Tiled: write frame
    XPSDataSet ->> tr_xrd_calc: calculate filtered frame
    XPSDataSet ->> Tiled: write filtered frame
    XPSDataSet ->> tr_xrd_calc: caluculatepeak fit
    XPSDataSet ->> Tiled: write peak fit
    deactivate XPSDataSet


    ZMQImageDispatcher ->> Dash App: notify new data available

    activate Dash App
    Dash App ->> Tiled: read VFFT
    Dash App ->> Tiled: read Sum
    Dash App ->> Tiled: read IVFFT
    Dash App ->> Tiled: read Peak Fit
    Dash App ->> Dash App: update slider
    deactivate Dash App
```

### Classes

```mermaid
classDiagram
    note for XPSDataSet "Module: tr_ap_xps.writer"
    class XPSDataSet {
        - run_id: str
        - runs_node: node
        - run_node: node
        - lines_raw_node: node
        + __init__(runs_node: node, run_id: str)
        - _get_or_create_container(tiled_node: node, name: str) node
        - _get_or_create_table(tiled_node: node, data_frame: pd.DataFrame, name: str) node
        + new_integrated_frame(curr_frame: np.array)
    }

    note for ZMQImageListener "Module: tr_ap_xps.listener"
    class ZMQImageListener {
        - zmq_pub_address: str
        - zmq_pub_port: int
        - frame_function: Callable[[int, np.ndarray], None]
        - stop: bool
        + __init__(zmq_pub_address: str="tcp://127.0.0.1", zmq_pub_port: int=5555, function: callable=None)
        + start()
        + stop()
    }

```
