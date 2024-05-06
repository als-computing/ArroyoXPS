# %%
# %%
import os
import shutil
from multiprocessing import Pool

import dill
import misc.trs_refactor as trs
import numcodecs
import numpy as np

# %%
import zarr
from frame_utils import get_frame_data

# from ttictoc import tic, toc

# %%
# Specify the path to your JSON file (adjust as necessary)
path = "."  # Folder where "Metadata 00012.json" is located
name = "Metadata"
number = 12
ext = "json"

# Instantiate the Metadata object
metadata_instance = trs.Metadata(path, name, number, ext)


# %%
""" Read a frame from a Frame Stream
MAKE sure you don't put a space after "Frame Stream" even so the filename is "Frame Stream " followed by the number
The number also to be 12 NOT 00012 like the filename """

frame_stream = trs.FrameStream(path=".", name="Frame Stream", number=12, ext="bin")
ccd_image, normalization = frame_stream.__frame_data__(frame_i=0)


# %%
""" Read the averaged spectrum from an ESpec Stream averaged """

espec_stream = trs.ESpecStream(path=".", name="ESpectrum Stream", number=12, ext="bin")


""" Extract the scan for frame_i = 0"""
espec_data, normalization = espec_stream.__espec_data__(frame_i=0)


espec_data.shape[0]


# %%

# Assuming espec_stream is your ESpecStream object initialized correctly
# And assuming total_line_scans represents the total number of frames

line_scans = []
for frame_i in range(int(espec_data.shape[0])):  # Ensure it's an integer
    espec_data, normalization = espec_stream.__espec_data__(frame_i)
    line_scans.append(espec_data)

# Convert the list of line scans into a 2D NumPy array
image_data = np.vstack(line_scans)  # Stack vertically

# If you need to transpose the image (depending on the orientation you need)
# image_data = image_data.T

# Define dataset parameters
n_frames = 400
path = "."
name = "Frame Stream"
number = 12
ext = "bin"
# Define the dimensions of a frame
frame_height = frame_stream.n_y  # Height of a frame,
frame_width = frame_stream.n_x  # Width of a frame,


zarr_directory = "./test_faster.zarr"

# Check if the Zarr directory exists, create if it does not
if not os.path.exists(zarr_directory):
    os.makedirs(zarr_directory)
# If it should be empty/clean before starting, clear it
else:
    shutil.rmtree(zarr_directory)
    os.makedirs(zarr_directory)

# Zarr dataset setup
root_group = zarr.open(zarr_directory, mode="w")
compressor = numcodecs.Zstd(level=3)
chunks = (1, frame_height, frame_width)  # Chunk size configuration
# To remove an existing dataset
if "frame_data" in root_group:
    del root_group["frame_data"]

# Then recreate it
frame_data_zarr = root_group.create_dataset(
    "frame_data",
    shape=(n_frames, frame_height, frame_width),
    chunks=chunks,
    dtype="float32",
    compressor=compressor,
)


def write_frame_to_zarr_serialized(args_serialized):
    # Deserialize the arguments
    args = dill.loads(args_serialized)
    frame_i, path, name, number, ext = args
    # Logic to open the Zarr dataset and write the frame data
    frame_data = get_frame_data(frame_i, path, name, number, ext)
    # Since we're modifying a global object, ensure this operation is safe if using actual multiprocessing
    frame_data_zarr[frame_i, :, :] = frame_data


if __name__ == "__main__":
    num_cores = os.cpu_count()
    print(f"Number of cores available: {num_cores}")

    # Prepare the arguments and serialize them
    args_list_serialized = [
        dill.dumps((frame_i, path, name, number, ext)) for frame_i in range(n_frames)
    ]

    # Use Pool to process data in parallel
    with Pool(processes=num_cores) as pool:
        # Map the serialized arguments to the worker function
        pool.map(write_frame_to_zarr_serialized, args_list_serialized)

    print("Parallel data processing with dill serialization completed.")
