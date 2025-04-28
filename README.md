# Real Time AP-XPS Service
This repository maintains a service that will the integrate with Beamline Control System for the new Real Time Ambient Pressure XRay Photon Spectroscopy instrument at the ALS.
``` mermaid

graph LR
    LabVIEW -->|ZMQ PUB| LabviewListener
    LabviewListener --> XPSO[XPSOperator]
    XPSO --> XPWS[XPSWSResultPublisher]
    XPWS -->|WebSocket| Browser
    XPSO --> TiledPublisher
    TiledPublisher-->|HTTP| Tiled


```


# Project Documentation
Project documentation is maintained in this repository. This includes:

- [User Stories](./docs/user_strories.md) captures user requirements in story format.

- [Dictionary](./docs/dictionary.md) captures terminology used in this project.

- [System Components](./docs/system_components.md) Describes the components of system maintained in this repository.

- [Design](./docs/design.md) Design notes and diagrams for this system.



# How to Run
For this section, we assume that you have `docker` or `podman`, and a way to run a `docker-compose` file. We reference the `docker-compose` command, but this could be `podman-compose` as well. However, `podman` is experimental for this.

0. Until Arroyo is public, you'll need to clone it locally (assuming you have read permission on it). This has to be done for development, and to build and run the containers.

```
git clone git@github.com:als-computing/arroyo.git
pip install
```

1. Adjust .env settings
Copy the file `.env.example` to `.env`. These settings will be picked up by docker-compose. You'll need to provide a very unique token for `TILED_SINGLE_USER_API_KEY`. A good way to generate this is:

```
openssl rand -hex 20
```

2. Start everything


The `docker-compose.yaml` file contains the following services:
- `tiled` a data server where result information gets saved
- `processor` a service that subscribes on a ZMQ pub/sub socket for raw data from Labview, processes the data, and publishes it again on a ZMQ pub/sub socket
- `wspublisher` a service that subscribtes to the Result ZMQ publisher and republishes result information to websockets, available for cnosumption by various clients, including web browsers
- `frontend` - an nginx server that serves the frontend browser application
- `tiled_writer` - TBD, a service that subscribtes to the Result ZMQ publisher and writes results to Tiled

With all that, the system can be started with a single command:

```
docker-compose up -d
```

## OPTIONAL
If you're not sitting at the beamline and want to test out the system, you can use the optional Labview simulator service. This is described in `docker-compose-simulator.yaml`. To start this up:

```
docker-compose -f docker-compose-simulator.yaml up -d
```

# Developer Setup
If you are developing this library, there are a few things to note.

1. Install development dependencies:

```
pip install .[dev]
```

2. Install pre-commit
This step will setup the pre-commit package. After this, commits will get run against flake8, black, isort.

```
pre-commit install
```

3. (Optional) If you want to check what pre-commit would do before commiting, you can run:

```
pre-commit run --all-files
```

4. To run test cases:

```
python -m pytest
```

# Notebook Setup
To run the notebooks in `examples` folder, install jupyter notebook dependencies:

```
pip install .[notebook]
```

The `Explore_data_write_zarr.ipynb` converts the raw `bin` formated data into `zarr` format.

The `example_peak_detection_plot.ipynb` read the example `test_array_300_1131.npy` file, run the peak detection code, and plot the location of detected peaks.

# Test Simulator
This repo contains a test ZMQ publisher that mimics the frame-producing ZMQ publisher that we expect to see from LabView.

To test it:
1. Create a python environment and activate it (using env, conda or others).
2. Install this package with dependencies by typing:

```
pip install .
```

3. Start the listener through docker-compose (above).

4. Start the simulator:
```
python -m tr_ap_xps.simulator

```

Now, if the listener is listening on `tcp://127.0.0.1:5555` then the simulator will publish to it.


# Copyright

TR-XPS Realtime Analysis Tool (ArroyoXPS) Copyright (c) 2025, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy). 
All rights reserved.

If you have questions about your rights to use or distribute this software,
please contact Berkeley Lab's Intellectual Property Office at
IPO@lbl.gov.

NOTICE.  This Software was developed under funding from the U.S. Department
of Energy and the U.S. Government consequently retains certain rights.  As
such, the U.S. Government has been granted for itself and others acting on
its behalf a paid-up, nonexclusive, irrevocable, worldwide license in the
Software to reproduce, distribute copies to the public, prepare derivative 
works, and perform publicly and display publicly, and to permit others to do so.