"""
Objects and functions to read and process Time Resolved Scienta data acquisition files
"""
import math
import os
import struct
import json
import numpy as np
import matplotlib.pyplot as plt

class AcqFile:
    """
    Object that represents the file for an acquisition consisting of repeated shots
    """
    def __init__(self, path, file_number):
        self.file_name = None
        self.frame_size = None
        self.n_y = None
        self.n_x = None
        self.pixel_size = None
        self.extra_bytes_per_frame = None
        self.md_dt = None
        self.num_shots = None
        self.frames_pershot = None
        self.num_frames = None
        self.__norm_array__ = None

        self.path = path
        self.file_number = file_number
        self.metafile = path + f"Metadata {self.file_number:05d}.json"
        self.datafile = path + f"Frame Stream {self.file_number:05d}.bin"
        self.especfile = path + f"ESpectrum Stream {self.file_number:05d}.bin"

        self.__init_metadata__()
        return

    def __init_metadata__(self):
        with open(self.metafile) as f:
            self.metadata = json.loads(f.read())

        for k, v in self.metadata.items():
            key = 'md_' + str.lower(k).replace(' ', '_')
            self.__dict__[key] = v

        if 'roi' not in self.__dict__:
            self.roi = self.md_rectangle

        self.roi_r = self.roi['Right']
        self.roi_l = self.roi['Left']
        self.roi_t = self.roi['Top']
        self.roi_b = self.roi['Bottom']

        self.tkeys = ["F_Trigger", "F_Un-Trigger", "F_Dead", "F_Reset"]
        self.kind = self.md_stream
        return

    def __init_sizes__(self):
        self.file_size = os.path.getsize(self.file_name)

        self.frame_size = self.n_x * self.n_y * self.pixel_size

        # frame_size doesn't include nx (and ny and norm). nx (and ny) are included before EACH frame. Norm is after.
        self.num_frames = self.file_size / (self.frame_size + self.extra_bytes_per_frame)
        self.frames_pershot = self.md_f_reset
        self.num_shots = self.num_frames / self.frames_pershot
        return

    def triggers(self):
        return [self.md_dt * self.metadata[key] for key in self.tkeys]

    def __repr__(self):
        ttypes = ['Pre-trigger (s)', 'Post-trigger (s)', "Relaxation (s)", "Dead Time (s)"]

        ts = [f"==   {typ:16s}: {self.metadata[k] * self.md_dt:3.3f}\n" for (typ, k) in zip(ttypes, self.tkeys)]
        s = (
            f"==   Num Frames      : {self.num_frames}\n"
            f"==   Frames / shot   : {self.frames_pershot}\n"
            f"==   Num Shots       : {self.num_shots:.2f}\n"
            f"==   Time / shot (s) : {self.frames_pershot * self.md_dt:.2f}\n"
            f"==   Total time (s)  : {self.num_frames * self.md_dt:.2f}\n"
            f"==   (Nx, Ny)        : ({self.n_x}, {self.n_y})\n"
            f"==   Bytes / pixel   : {self.pixel_size}\n"
            f"==   Frame Size (KB) : {self.frame_size / 1E3:.1f}\n"

        )
        return ("=== Time Resolved Scienta Acquisition File\n"
                f"==   File number     : {self.file_number:05d}\n"
                f"==   File name       : {self.file_name}\n"
                f"==   Stream kind     : {self.kind}\n"
                ) + ''.join(ts) + s + '\n'

    def total_time(self):
        return self.num_frames * self.md_dt

    def normalization_array(self):
        if self.__norm_array__ is not None:
            return self.__norm_array__

        norm_list = []
        with open(self.file_name, "rb") as f:
            for frame_i in range(int(self.num_frames)):
                offset = (frame_i + 1) * (self.frame_size + self.extra_bytes_per_frame) - 8     # go one frame past, then back one double's worth
                f.seek(offset)

                raw_bytes = f.read(8)  # 8 byte double for normalization value
                normalization = struct.unpack(">d", raw_bytes)[0]  # big-endian double
                norm_list.append(normalization)

        self.__norm_array__ = np.array(norm_list)
        return self.__norm_array__


class AcqFile1D(AcqFile):
    def __init__(self, path, file_number):
        super().__init__(path, file_number)

        self.file_name = self.especfile
        self.kind = "Energy Spectra"

        self.__init_sizes__()

        return

    def __init_sizes__(self):
        self.n_y = 1
        self.pixel_size = 4     # u32 is 4 bytes per pixel
        self.extra_bytes_per_frame = 4 + 8  # 4 byte integer length + 8 byte double normalization
        with open(self.especfile, "rb") as f:
            self.n_x = int.from_bytes(f.read(4), "big")
        super().__init_sizes__()
        return

    def __espec_data__(self, frame_i, verbose=False, **kwargs):
        if verbose:
            print(f"Reading frame {frame_i}", end='\r')

        with open(self.especfile, "rb") as f:
            offset = frame_i * (self.frame_size + self.extra_bytes_per_frame) + 4   # 4 byte length
            f.seek(offset)

            raw_bytes = f.read(self.frame_size) # frame_size = n_x for 1D spectra
            espec = struct.unpack(f">{self.n_x}L", raw_bytes)

            raw_bytes = f.read(8)  # byte double for normalization value
            normalization = struct.unpack(">d", raw_bytes)[0]  # big-endian double

        return np.array(espec), normalization

    def e_spec(self, frame_i, normalize=False, roi=True, **kwargs):
        espec, norm = self.__espec_data__(frame_i, **kwargs)
        if roi:
            espec = espec[self.roi_l:(self.roi_r+1)]
        if normalize:
            espec = espec / norm
        return espec

    def plot_e_spec(self, frame_i, normalize=False, roi=True, **kwargs):
        e_spec = self.e_spec(frame_i, normalize=normalize, roi=roi, **kwargs)

        s = " normalized" if normalize else ""
        s += " roi" if roi else ""

        plt.plot(e_spec)
        plt.ylim(bottom=0)
        plt.title(f"File: {self.file_number}", loc='left')
        plt.title(f"Frame: {frame_i}{s}", loc='right')
        plt.xlabel("Energy (pixels)")
        plt.ylabel("dN/dE")
        plt.show()
        return e_spec


class AcqFile2D(AcqFile):

    def __init__(self, path, file_number):
        super().__init__(path, file_number)

        self.file_name = self.datafile

        self.__init_sizes__()
        return

    def __init_sizes__(self):
        self.pixel_size = 1  # u8 is 1 bytes/pixel
        self.extra_bytes_per_frame = 4 + 4 + 8  # two 4 byte integer lengths + 8 byte double normalization
        with open(self.datafile, "rb") as f:
            self.n_y = int.from_bytes(f.read(4), "big")
            self.n_x = int.from_bytes(f.read(4), "big")
        super().__init_sizes__()
        return

    def __frame_data__(self, frame_i, verbose=False, **kwargs):
        if verbose:
            print(f"Reading frame {frame_i}", end='\r')

        with open(self.datafile, "rb") as f:
            offset = frame_i * (self.frame_size + 16) + 8   # 16 = 2*(4 byte lengths) + 8 byte double norm
            f.seek(offset)

            raw_bytes = f.read(self.frame_size)
            #
            # for each row, unpack n_x pixels into an array
            # the result is an array of rows
            #
            # use numpy stack to convert to 2D array of pixels
            col_size = self.pixel_size * self.n_x
            ccd_rows = [struct.unpack(f">{self.n_x}B", raw_bytes[i * col_size:(i + 1) * col_size]) for i in
                        range(self.n_y)]
            ccd_image = np.stack(ccd_rows)

            raw_bytes = f.read(8)  # byte double for normalization value
            normalization = struct.unpack(">d", raw_bytes)[0]  # big-endian double

        return ccd_image, normalization

    def normalization(self, frame_i):
        ccd_image, normalization = self.__frame_data__(frame_i)
        return normalization

    # def normalization_array(self):
    #     if hasattr(self, "__norm_array__"):
    #         return self.__norm_array__
    #
    #     norm_list = []
    #     with open(self.datafile, "rb") as f:
    #         for frame_i in range(int(self.num_frames)):
    #             offset = frame_i * (self.frame_size + 16) + 8 + self.frame_size  # go just past the frame data
    #             f.seek(offset)
    #
    #             raw_bytes = f.read(8)  # 8 byte double for normalization value
    #             normalization = struct.unpack(">d", raw_bytes)[0]  # big-endian double
    #             norm_list.append(normalization)
    #
    #     self.__norm_array__ = np.array(norm_list)
    #     return self.__norm_array__
    #
    def frame(self, frame_i, normalize=False, roi=True, **kwargs):
        ccd_image, normalization = self.__frame_data__(frame_i, **kwargs)
        if roi:
            ccd_image = ccd_image[self.roi_t:(self.roi_b+1), self.roi_l:(self.roi_r+1)]
        if normalize:
            ccd_image = ccd_image / normalization
        return ccd_image

    def e_spec(self, frame_i, **kwargs):
        frame = self.frame(frame_i, **kwargs)
        # integrate out angles
        return [np.sum(col) for col in np.transpose(frame)]

# This function is too slow. Try rewriting with ctypes. Until then use LabView TRS View to make E spectra file
# from
    # def make_spectrum_file(self, rebuild=False, roi=True, **kwargs):
    #     self.spectrum_file = self.path + f"Energy Spectra {self.file_number:05d}.bin"
    #     if os.path.exists(self.spectrum_file) and not rebuild:
    #         print("Spectrum file already exists. Use rebuild=True option to make it again.")
    #         return
    #
    #     with open(self.spectrum_file, "wb") as outf:
    #         for frame_i in range(int(self.num_frames)):
    #             ccd_image, normalization = self.__frame_data__(frame_i, **kwargs)
    #             if roi:
    #                 ccd_image = ccd_image[self.roi_t:(self.roi_b + 1), self.roi_l:(self.roi_r + 1)]
    #
    #             spectrum = [np.sum(col) for col in np.transpose(ccd_image)]
    #             #######################################################
    #             # write the length of the spectrum first
    #             raw_bytes = struct.pack(">i", len(spectrum))
    #             outf.write(raw_bytes)
    #
    #             # write the spectrum as U32 integers
    #             raw_bytes = struct.pack(f">{len(spectrum)}L", *spectrum)
    #             outf.write(raw_bytes)
    #
    #             # write the normalization as 4 byte double (this is why we don't normalize in this function
    #             #  otherwise we risk the user normalizing twice unwittingly)
    #             raw_bytes = struct.pack(">d", normalization)

    def shot(self, shot_i, **kwargs):
        start = shot_i * self.frames_pershot
        stop = start + self.frames_pershot
        return np.stack([self.e_spec(f_i, **kwargs) for f_i in range(start, stop)])

    #    def integrate_shots(self, shot_iterable):

    def plot_frame(self, frame_i, normalize=False, roi=True, **kwargs):
        # plot the whole frame
        frame = self.frame(frame_i, normalize=normalize, roi=roi, **kwargs)

        s = " normalized" if normalize else ""
        s += " roi" if roi else ""

        plt.imshow(frame, cmap='gray')#, vmin=0, vmax=np.median(frame))
        plt.title(f"File: {self.file_number}", loc='left')
        plt.title(f"Frame: {frame_i}{s}", loc='right')
        plt.xlabel("Energy (pixels)")
        plt.ylabel("Angle (pixels)")
        plt.show()
        return frame

    def plot_e_spec(self, frame_i, normalize=False, roi=True, **kwargs):
        e_spec = self.e_spec(frame_i, normalize=normalize, roi=roi, **kwargs)

        s = " normalized" if normalize else ""
        s += " roi" if roi else ""

        plt.plot(e_spec)
        plt.ylim(bottom=0)
        plt.title(f"File: {self.file_number}", loc='left')
        plt.title(f"Frame: {frame_i}{s}", loc='right')
        plt.xlabel("Energy (pixels)")
        plt.ylabel("dN/dE")
        plt.show()
        return e_spec
