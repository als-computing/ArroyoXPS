# frame_utils.py
import misc.trs_refactor as trs


def get_frame_data(frame_i, path, name, number, ext):
    # Your existing function code here
    frame_stream = trs.FrameStream(path, name, number, ext)
    return frame_stream.__frame_data__(frame_i)[0]
