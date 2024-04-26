"""
Objects and functions to read and process Time Resolved Scienta data acquisition files
"""
import math
import os
import struct
import json
import numpy as np
import matplotlib.pyplot as plt


class Metadata:
    def __init__(self, path, name, number, ext):
        self.path = path
        self.file_number = number
        self.file_name = Stream.check_file(path, name, number, ext)

        with open(self.file_name) as f:
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

    def __repr__(self):
        return json.dumps(self.metadata, indent=4)

class Stream:
    """
    Object representing a streamed acquisition
    """

    def __init__(self, path, name, number, ext):
        self.path = path
        self.file_number = number
        self.file_name = Stream.check_file(path, name, number, ext)
        self.file_size = os.path.getsize(self.file_name)

        self.frame_size = None
        self.n_x = None
        self.n_y = None
        self.element_size = None
        self.extra_bytes_per_frame = None
        self.md_dt = None
        self.num_shots = None
        self.frames_pershot = None
        self.num_frames = None
        self.__norm_array__ = None

        self.__init_sizes__()
        return

    def __init_sizes__(self):
        self.frame_size = self.n_x * self.n_y * self.element_size

        # frame_size doesn't include nx (and ny and norm). nx (and ny) are included before EACH frame. Norm is after.
        self.num_frames = self.file_size / (self.frame_size + self.extra_bytes_per_frame)
        return

    def __repr__(self):
        s = (
            f"=== Stream           "
            f"==   File number     : {self.file_number:05d}\n"
            f"==   File name       : {self.file_name}\n"
            f"==   File size       : {self.file_size}\n"
            f"==   Stream kind     : {self.kind}\n"
            f"==   Num Frames      : {self.num_frames}\n"
            f"==   (Nx, Ny)        : ({self.n_x}, {self.n_y})\n"
            f"==   Bytes / element : {self.element_size}\n"
            f"==   Frame Size      : {self.frame_size}\n"
            f"==   Extra bytes / fr: {self.extra_bytes_per_frame}\n"
        )
        return s

    @staticmethod
    def check_file(path, name, number, ext):
        fqn = os.path.join(path, f"{name} {number:05d}.{ext}")
        #fqn = path + f"{name} {number:05d}.{ext}"
        return fqn if os.path.isfile(fqn) else None

    def normalization(self, frame_i):
        with open(self.file_name, "rb") as f:
            offset = (frame_i+1) * (self.frame_size + self.extra_bytes_per_frame) - 8   # 8 byte double normalization
            f.seek(offset)

            raw_bytes = f.read(8)  # byte double for normalization value
            normalization = struct.unpack(">d", raw_bytes)[0]  # big-endian double

        return normalization


class ESpecStream(Stream):
    def __init__(self, path, name, number, ext):
        super().__init__(path, name, number, ext)

        self.kind = "Energy Spectra"
        return

    def __init_sizes__(self):
        self.element_size = 4  # u32 is 4 bytes/pixel
        self.extra_bytes_per_frame = 4 + 8  # one 4 byte integer length + 8 byte double normalization
        self.n_y = 1
        with open(self.file_name, "rb") as f:
            self.n_x = int.from_bytes(f.read(4), "big")
        super().__init_sizes__()
        return

    def __espec_data__(self, frame_i, verbose=False, **kwargs):
        with open(self.file_name, "rb") as f:
            offset = frame_i * (self.frame_size + self.extra_bytes_per_frame) + 4   # 4 byte length
            f.seek(offset)

            raw_bytes = f.read(self.frame_size)
            espec = struct.unpack(f">{self.n_x}L", raw_bytes)

            raw_bytes = f.read(8)  # byte double for normalization value
            normalization = struct.unpack(">d", raw_bytes)[0]  # big-endian double

        return np.array(espec), normalization


class FrameStream(Stream):
    def __init__(self, path, name, number, ext):
        super().__init__(path, name, number, ext)

        self.kind = "CCD Image Stream"
        return

    def __init_sizes__(self):
        self.element_size = 1  # u8 is 1 bytes/pixel
        self.extra_bytes_per_frame = 4 + 4 + 8  # two 4 byte integer lengths + 8 byte double normalization
        with open(self.file_name, "rb") as f:
            self.n_y = int.from_bytes(f.read(4), "big")
            self.n_x = int.from_bytes(f.read(4), "big")
        super().__init_sizes__()
        return

    def __frame_data__(self, frame_i):
        with open(self.file_name, "rb") as f:
            offset = frame_i * (self.frame_size + 16) + 8   # 16 = 2*(4 byte lengths) + 8 byte double norm
            f.seek(offset)

            raw_bytes = f.read(self.frame_size)
            #
            # for each row, unpack n_x pixels into an array
            # the result is an array of rows
            #
            # use numpy stack to convert to 2D array of pixels
            col_size = self.element_size * self.n_x
            ccd_rows = [struct.unpack(f">{self.n_x}B", raw_bytes[i * col_size:(i + 1) * col_size]) for i in
                        range(self.n_y)]
            ccd_image = np.stack(ccd_rows)

            raw_bytes = f.read(8)  # byte double for normalization value
            normalization = struct.unpack(">d", raw_bytes)[0]  # big-endian double

        return ccd_image, normalization


class Acq:
    def __init__(self, path, number):

        self.__norm_array__ = None

        self.path = path
        self.file_number = number

        self.meta_d = Metadata(path, "Metadata", number, "json")
        if self.meta_d is None:
            raise Exception("Metadata file not found. Object instantiation halted.")

        try:
            self.frame_s = FrameStream(path, "Frame Stream", number, "bin")
        except:
            self.frame_s = None

        try:
            self.espec_s = ESpecStream(path, "ESpectrum Stream", number, "bin")
        except:
            self.espec_s = None

        if self.frame_s is None and self.espec_s is None:
            raise Exception("Cannot find a data file, neither frame or spectrum. Object instantiation halted.")

        self.frames_pershot = self.meta_d.md_f_reset
        self.num_frames = self.frame_s.num_frames if self.frame_s else self.espec_s.num_frames
        self.num_shots = self.num_frames / self.frames_pershot

    def __repr__(self):
        s = (
            f"=== Acquisition Object\n"
            f"==   Frames / shot   : {self.frames_pershot}\n"
            f"==   Num Shots       : {self.num_shots:.3f}\n"
            f"==   Time / shot (s) : {self.frames_pershot * self.meta_d.md_dt:.3f}\n"
            f"==   Total time (s)  : {self.num_frames * self.meta_d.md_dt:.3f}\n"
            f"==   Num Frames      : {self.num_frames}\n"
        )
        return s
        # ttypes = ['Pre-trigger (s)', 'Post-trigger (s)', "Relaxation (s)", "Dead Time (s)"]

        # ts = [f"==   {typ:16s}: {self.metadata[k] * self.md_dt:3.3f}\n" for (typ, k) in zip(ttypes, self.tkeys)]

    def total_time(self):
        return self.num_frames * self.meta_d.md_dt

    def normalization_array(self):
        if self.__norm_array__:
            return self.__norm_array__

        norm_list = []
        stream = self.espec_s if self.espec_s else self.frame_s
        with open(stream.file_name, "rb") as f:
            for frame_i in range(int(stream.num_frames)):
                # go one frame past, then back one double's worth
                offset = (frame_i + 1) * (stream.frame_size + stream.extra_bytes_per_frame) - 8
                f.seek(offset)

                raw_bytes = f.read(8)  # 8 byte double for normalization value
                normalization = struct.unpack(">d", raw_bytes)[0]  # big-endian double
                norm_list.append(normalization)

        self.__norm_array__ = np.array(norm_list)
        return self.__norm_array__

    def frame(self, frame_i, normalize=False, roi=True, verbose=False, **kwargs):
        if self.frame_s is None:
            raise Exception("No Frame-Stream object for this acquisition. No frame data found.")

        if verbose:
            print(f"Reading frame {frame_i}", end='\r')

        ccd_image, normalization = self.frame_s.__frame_data__(frame_i)
        if roi:
            ccd_image = ccd_image[self.meta_d.roi_t:(self.meta_d.roi_b+1), self.meta_d.roi_l:(self.meta_d.roi_r+1)]
        if normalize:
            ccd_image = ccd_image / normalization
        return ccd_image

    def spectrum(self, frame_i, normalize=False, roi=True, verbose=False, **kwargs):
        if self.espec_s:
            if verbose:
                print(f"Reading energy spectrum {frame_i}", end='\r')

            espec, norm = self.espec_s.__espec_data__(frame_i, **kwargs)
            if roi:
                espec = espec[self.meta_d.roi_l:(self.meta_d.roi_r + 1)]
            if normalize:
                espec = espec / norm
            return espec
        else:
            frame = self.frame(frame_i, normalize=normalize, roi=roi, verbose=verbose, **kwargs)
            # integrate out angles
            return [np.sum(col) for col in np.transpose(frame)]

    def shot(self, shot_i, **kwargs):
        start = shot_i * self.frames_pershot
        stop = start + self.frames_pershot
        return np.stack([self.spectrum(e_i, **kwargs) for e_i in range(start, stop)])

    def plot_spectrum(self, frame_i, normalize=False, roi=True, **kwargs):
        e_spec = self.spectrum(frame_i, normalize=normalize, roi=roi, **kwargs)

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

    def plot_frame(self, frame_i, normalize=False, roi=True, **kwargs):
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

