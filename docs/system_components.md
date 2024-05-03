# Architecture

| Service Name                   | Description                                                                                          |
|--------------------------------|------------------------------------------------------------------------------------------------------|
| Tiled Server                   |                                                                                                      |
| Time-Resolved XRD Service      | A service that listens for new frames, algorithms, and notifies the UI of new results. This service will integrate with the LabView control system at the beamline.                |
| Time Resolved XRD Calculator   | A library that takes frames, performs calculations, and writes results to Tiled                       |
| Time-Resolved XRD UI           | A dash application showing the current results of the scan, pulled from Tiled                         |

