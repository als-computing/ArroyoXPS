# User Stories
This repository aims to fullfil requirements based on the following user stories.

## Experiment Monitoring
A Beamline User has LabView UI and a web browser open. They enter scan parameters, including the cycle number in LabView and begin the scan. As frames are produced, the user sees the web browser UI update showing calculations that have been done periodically during the scan. As the scan frames hits the cycle number, the UI updates to show current values for:

- current 1D frame integration
- current VFFT
- curren sum from the region of interest
- current IVFFT
- current Peak Fit


Each time the UI updates, a frame number slider updates to the current number as the max, allowing the user to scroll back and forth to review the updates. When the user sees the peak fit converge to a happy space, they stop the scan in the LabView UI.