start = {
    "msg_type": "start",
    "Binding Energy (eV)": 2.0,
    "frame_per_cycle": 2,
    "scan_name": "test",
}

image_info = {
    "Frame Number": 1,
    "Width": 5,
    "Height": 10,
    "data_type": "int32",
}

stop = {
    "msg_type": "metadata",
    "metadata": {
        "F_Trigger": 1,
        "F_Un-Trigger": 2,
        "F_Dead": 3,
        "F_Reset": 4,
        "CCD_nx": 1392,
        "CCD_ny": 1040,
        "Pass Energy": 200,
        "Center Energy": 3540,
        "Offset Energy": -0.837,
        "Lens Mode": "X6-26Mar2022-test",
        "Rectangle": {
            "Left": 148,
            "Top": 385,
            "Right": 1279,
            "Bottom": 654,
            "Rotation": 0,
        },
        "Notes": "Four stars, no notes",
        "dt": 0.0820741786426572,
        "Photon Energy": 4000.00301929836,
        "Binding Energy": 460,
        "File Ver": "1.0.0",
        "Stream": "Full Frame (FF)",
    },
}
