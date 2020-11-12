"""
regn.data.csu_data
==================

This module provides two classes to read in the binary data used
for the training of the GPROF algorithm.
"""
from pathlib import Path
import re

import numpy as np
import netCDF4


def check_sample(data):
    """
    Check that brightness temperatures of a sample are within a valid range.

    Arguments:
        data: The data array containing the data of one training sample.

    Return:
        Bool indicating whether the given sample contains valid brightness
        temperatures.
    """
    return all([data[i] > 0 and data[i] < 1000 for i in range(13, 26)])


def get_files(base_path, year, month, day):
    """
    Iterate over files for specific year, month and day.

    Args:
        base_path(``pathlib.Path``): Root folder containing the binary data
            files.
        year(``int``): Year as two-digit integer.
        month(``int``): Month as two-digit integer.
        day(``int``): The day as two-digit integer.
    """
    base_path = Path(base_path)
    return base_path.glob(f"{year:02d}{month:02d}/"
                          f"*20{year:02d}{month:02d}{day:02d}*.dat")

###############################################################################
# GMI Binary data
###############################################################################


HEADER_TYPES_GMI = [('satcode', 'S5'),
                    ('sensor', 'S5')]
HEADER_TYPES_GMI += [(f'freq_{i}', "f4") for i in range(13)]
HEADER_TYPES_GMI += [(f'viewing_angle_{i}', "f4") for i in range(13)]

PIXEL_TYPES_GMI = [('nx', 'i4'),
                   ('ny', 'i4'),
                   ('year', 'i4'),
                   ('month', 'i4'),
                   ('day', 'i4'),
                   ('hour', 'i4'),
                   ('minute', 'i4'),
                   ('second', 'i4'),
                   ('lat', 'f4'),
                   ('lon', 'f4'),
                   ('sfccode', 'i4'),
                   ('tcwv', 'f4'),
                   ('T2m', 'f4')]
PIXEL_TYPES_GMI += [(f'Tb_{i}', 'f4') for i in range(13)]
PIXEL_TYPES_GMI += [(f'sfcprcp', 'f4'),
                    (f'cnvprcp', 'f4')]


class GMIBinaryFile:
    """
    Class to extract data from GMI CSU binary files and store to
    NetCDF file.
    """
    def __init__(self, filename):
        """
        Open CSU binary file containing GPROF training data for
        GMI sensor..

        Args:
            filename(``pathlib.Path``): The file to open.
        """
        self.header = np.memmap(filename,
                                dtype=HEADER_TYPES_GMI,
                                mode="r",
                                shape=(1,))
        self.pixels = np.memmap(filename,
                                dtype=PIXEL_TYPES_GMI,
                                offset= 10 + 8 * 13,
                                mode="r")

    @classmethod
    def create_output_file(cls, filename):
        """
        Create NetCDF output file.

        Args:
            filename(``pathlib.Path``): The filename of the output file.
        """
        file = netCDF4.Dataset(filename, "w")
        file.createDimension("channels", size=13)
        file.createDimension("samples", size=None)
        file.createVariable("brightness_temperature",
                            "f4",
                            dimensions=("samples",
                                        "channels"))
        file.createVariable("nx", "i4", dimensions=("samples",))
        file.createVariable("ny", "i4", dimensions=("samples",))
        file.createVariable("tbs_min", "f4", dimensions=("channels"))
        file.createVariable("tbs_max", "f4", dimensions=("channels"))
        file.createVariable("latitude", "f4", dimensions=("samples",))
        file.createVariable("longitude", "f4", dimensions=("samples",))
        file.createVariable("surface_type", "f4", dimensions=("samples",))
        file.createVariable("tcwv", "f4", dimensions=("samples",))
        file.createVariable("t2m", "f4", dimensions=("samples",))
        file.createVariable("surface_precipitation",
                            "f4",
                            dimensions=("samples",))
        file.createVariable("convective_precipitation",
                            "f4",
                            dimensions=("samples",))
        # Also include date.
        file.createVariable("year", "i4", dimensions=("samples",))
        file.createVariable("month", "i4", dimensions=("samples",))
        file.createVariable("day", "i4", dimensions=("samples",))
        file.createVariable("hour", "i4", dimensions=("samples",))
        file.createVariable("minute", "i4", dimensions=("samples",))
        file.createVariable("second", "i4", dimensions=("samples",))

        file["tbs_min"][:] = 1e30
        file["tbs_max"][:] = 0.0
        return file


    def write_to_file(self, file, samples=-1):
        """
        Write data to NetCDF file.

        Arguments
            file(``netCDF4.Dataset``): File handle to the output file.
            samples(``int``): How many samples to extract from the file.
        """
        v_tbs = file.variables["brightness_temperature"]
        v_lats = file.variables["latitude"]
        v_lons = file.variables["longitude"]
        v_sfccode = file.variables["surface_type"]
        v_tcwv = file.variables["tcwv"]
        v_t2m = file.variables["t2m"]
        v_surf_precip = file.variables["surface_precipitation"]
        v_conv_precip = file.variables["convective_precipitation"]
        v_tbs_min = file.variables["tbs_min"]
        v_tbs_max = file.variables["tbs_max"]
        v_nx = file.variables["nx"]
        v_ny = file.variables["ny"]

        v_year = file.variables["year"]
        v_month = file.variables["month"]
        v_day = file.variables["day"]
        v_hour = file.variables["hour"]
        v_minute = file.variables["minute"]
        v_second = file.variables["second"]

        n_samples = len(self.pixels)
        if samples < 0:
            samples = n_samples
        indices = np.random.permutation(np.arange(n_samples))

        n_extracted = 0
        for index in indices:
            if n_extracted >= samples:
                break
            if not check_sample(self.pixels[index]):
                continue
            d = self.pixels[index]
            i = file.dimensions["samples"].size

            v_year[i] = d[2]
            v_month[i] = d[3]
            v_day[i] = d[4]
            v_hour[i] = d[5]
            v_minute[i] = d[6]
            v_second[i] = d[7]

            v_lats[i] = d[8]
            v_lons[i] = d[9]
            v_sfccode[i] = d[10]
            v_tcwv[i] = d[11]
            v_t2m[i] = d[12]
            for j in range(13):
                tb = d[13 + j]
                v_tbs_min[j] = np.minimum(v_tbs_min[j], tb)
                v_tbs_max[j] = np.maximum(v_tbs_max[j], tb)
                v_tbs[i, j] = tb
            sp = d[26]
            v_surf_precip[i] = sp
            cp = d[27]
            v_conv_precip[i] = cp
            v_nx[i] = d["nx"]
            v_ny[i] = d["ny"]
            n_extracted += 1

###############################################################################
# MHS binary data
###############################################################################

HEADER_TYPES_MHS = [('satcode', 'S5'),
                    ('sensor', 'S5')]
HEADER_TYPES_MHS += [(f'freq_{i}', "f4") for i in range(5)]
HEADER_TYPES_MHS += [(f'viewing_angle_{i}', "f4") for i in range(10)]

PIXEL_TYPES_MHS = [('nx', 'i4'),
                   ('ny', 'i4'),
                   ('year', 'i4'),
                   ('month', 'i4'),
                   ('day', 'i4'),
                   ('hour', 'i4'),
                   ('minute', 'i4'),
                   ('second', 'i4'),
                   ('lat', 'f4'),
                   ('lon', 'f4'),
                   ('sfccode', 'i4'),
                   ('tcwv', 'f4'),
                   ('T2m', 'f4')]
PIXEL_TYPES_MHS += [(f'Tb_{i}_{j}', 'f4') for i in range(10) for j in range(5)]
PIXEL_TYPES_MHS += [(f'sfcprcp_{i}', 'f4') for i in range(10)]
PIXEL_TYPES_MHS += [(f'cnvprcp_{i}', 'f4') for i in range(10)]


class MHSBinaryFile:
    """
    Class to extract data from MHS CSU binary files and store to
    NetCDF file.
    """
    def __init__(self, filename):
        """
        Open CSU binary file containing GPROF training data for
        MHS sensor.

        Args:
            filename(``pathlib.Path``): The file to open.
        """
        self.header = np.memmap(filename,
                                dtype=HEADER_TYPES_MHS,
                                mode="r",
                                shape=(1,))
        self.pixels = np.memmap(filename,
                                dtype=PIXEL_TYPES_MHS,
                                offset=70,
                                mode="r")

    @classmethod
    def create_output_file(cls, filename):
        """
        Create NetCDF output file.

        Args:
            filename(``pathlib.Path``): The filename of the output file.
        """
        file = netCDF4.Dataset(filename, "w")
        file.createDimension("viewing_angles", size=10)
        file.createDimension("channels", size=5)
        file.createDimension("samples", size=None)
        file.createVariable("brightness_temperature",
                            "f4",
                            dimensions=("samples",
                                        "viewing_angles",
                                        "channels"))
        file.createVariable("viewing_angles", "f4", dimensions=("viewing_angles",))
        file.createVariable("frequencies", "f4", dimensions=("channels",))

        file.createVariable("tbs_min", "f4", dimensions=("viewing_angles",
                                                         "channels"))
        file.createVariable("tbs_max", "f4", dimensions=("viewing_angles",
                                                         "channels"))
        file.createVariable("latitude", "f4", dimensions=("samples",))
        file.createVariable("longitude", "f4", dimensions=("samples",))
        file.createVariable("surface_type", "f4", dimensions=("samples",))
        file.createVariable("tcwv", "f4", dimensions=("samples"))
        file.createVariable("t2m", "f4", dimensions=("samples"))
        file.createVariable("surface_precipitation",
                            "f4",
                            dimensions=("samples",
                                        "viewing_angles"))
        file.createVariable("convective_precipitation",
                            "f4",
                            dimensions=("samples",
                                        "viewing_angles"))
        # Also include date.
        file.createVariable("year", "i4", dimensions=("samples",))
        file.createVariable("month", "i4", dimensions=("samples",))
        file.createVariable("day", "i4", dimensions=("samples",))
        file.createVariable("hour", "i4", dimensions=("samples",))
        file.createVariable("minute", "i4", dimensions=("samples",))
        file.createVariable("second", "i4", dimensions=("samples",))

        file["viewing_angles"][:] = [mhs_data.header[0][i] for i in range(7, 17)]
        file["frequencies"][:] = [mhs_data.header[0][i] for i in range(2, 7)]
        file["tbs_min"][:] = 1e30
        file["tbs_max"][:] = 0.0
        return file

    def write_to_file(self, file, samples=-1):
        """
        Write data to NetCDF file.

        Arguments
            file(``netCDF4.Dataset``): File handle to the output file.
            samples(``int``): How many samples to extract from the file.
        """
        v_tbs = file.variables["brightness_temperature"]
        v_lats = file.variables["latitude"]
        v_lons = file.variables["longitude"]
        v_sfccode = file.variables["surface_type"]
        v_tcwv = file.variables["tcwv"]
        v_t2m = file.variables["t2m"]
        v_surf_precip = file.variables["surface_precipitation"]
        v_conv_precip = file.variables["convective_precipitation"]
        v_tbs_min = file.variables["tbs_min"]
        v_tbs_max = file.variables["tbs_max"]

        v_year = file.variables["year"]
        v_month = file.variables["month"]
        v_day = file.variables["day"]
        v_hour = file.variables["hour"]
        v_minute = file.variables["minute"]
        v_second = file.variables["second"]

        n_samples = len(self.pixels)
        if samples < 0:
            samples = n_samples
        indices = np.random.permutation(np.arange(n_samples))

        n_extracted = 0
        for index in indices:
            if n_extracted >= samples:
                break
            if not check_sample(self.pixels[index]):
                continue
            d = self.pixels[index]
            i = file.dimensions["samples"].size

            v_year[i] = d[2]
            v_month[i] = d[3]
            v_day[i] = d[4]
            v_hour[i] = d[5]
            v_minute[i] = d[6]
            v_second[i] = d[7]

            v_lats[i] = d[8]
            v_lons[i] = d[9]
            v_sfccode[i] = d[10]
            v_tcwv[i] = d[11]
            v_t2m[i] = d[12]
            for j in range(10):
                for k in range(5):
                    tb = d[13 + j * 5 + k]
                    v_tbs_min[j, k] = np.minimum(v_tbs_min[j, k], tb)
                    v_tbs_max[j, k] = np.maximum(v_tbs_max[j, k], tb)
                    v_tbs[i, j, k] = tb
                sp = d[13 + 50 + j]
                v_surf_precip[i, j] = sp
                cp = d[13 + 60 + j]
                v_conv_precip[i, j] = cp
            n_extracted += 1

mhs_data = MHSBinaryFile("/home/simonpf/Dendrite/UserAreas/Teo/MHS/1409/MHS.CSU.20140902.002900.dat")

###############################################################################
# GPROF binary data
###############################################################################

HEADER_TYPES_GPROF = [('satcode', 'S5'),
                    ('sensor', 'S5')]
HEADER_TYPES_GPROF += [(f'freq_{i}', "f4") for i in range(5)]
HEADER_TYPES_GPROF += [(f'viewing_angle_{i}', "f4") for i in range(10)]

PIXEL_TYPES_GPROF = [('nx', 'i4'),
                   ('ny', 'i4'),
                   ('year', 'i4'),
                   ('month', 'i4'),
                   ('day', 'i4'),
                   ('hour', 'i4'),
                   ('minute', 'i4'),
                   ('second', 'i4'),
                   ('lat', 'f4'),
                   ('lon', 'f4'),
                   ('sfccode', 'i4'),
                   ('tcwv', 'f4'),
                   ('T2m', 'f4')]
PIXEL_TYPES_GPROF += [(f'Tb_{i}_{j}', 'f4') for i in range(10) for j in range(5)]
PIXEL_TYPES_GPROF += [(f'sfcprcp_{i}', 'f4') for i in range(10)]
PIXEL_TYPES_GPROF += [(f'cnvprcp_{i}', 'f4') for i in range(10)]

HEADER_TYPES_GPROF = [("satellite", "S12"),
                      ("sensor", "S12"),
                      ("preprocessor_version", "S12"),
                      ("algorithm_version", "S12"),
                      ("profile_database_file", "S128"),
                      ("radiometer_file", "S128"),
                      ("file_create_date", "S12"),
                      ("granule_start_date", "S12"),
                      ("granule_end_date", "S12"),
                      ("granule_number", "i4"),
                      ("num_scans", "i2"),
                      ("num_pixels", "i2"),
                      ("prof_struct_flag", "c"),
                      ("spares", "S51"),
                      ("num_species", "i1"),
                      ("num_temps", "i1"),
                      ("num_layers", "i1"),
                      ("num_profiles", "i1")]




def get_profile_types_gprof(n_species,
                            n_temps,
                            n_layers,
                            n_profiles):
    """
    Args:
        n_species: The number of hydrometeor species in the ifle.
        n_temps: The number of profile temperatures
        n_layers:  Number of layers of each profile.
        n_profiles: The number of profiles.

    Returns:
        List of tuples describing the dataformat for the profile information
        in a CSU GPROF binary file.

    """
    types = [('descriptions', "S20", (n_species, )),
             ('top_layers_heights', "f4", (n_layers, )),
             ('temp', "f4", (n_temps,)),
             ('profiles', "f4", (n_species, n_temps, n_layers, n_profiles))]
    return types


def get_pixel_types_gprof(n_species):
    """
    Args:
        n_species: The number of hydrometeors species in the retrieval.

    Returns:

        List of tuples describing the dataformat for each retrieved pixel
        in a CSU GPROF binary file.
    """
    pixel_types = [('pixel_status', 'b'),
                   ('qualitty_flag', 'b'),
                   ('l1_quality_flag', 'b'),
                   ('surface_type_index', 'b'),
                   ('total_water_vapor_index', 'b'),
                   ('probability_of_precipitation', 'b'),
                   ('temp_2m_index', 'i2'),
                   ('cape', 'i2'),
                   ('sun_glint_angle', 'b'),
                   ('spare_1', 'b'),
                   ('latitude', 'f4'),
                   ('longitude', 'f4'),
                   ('surface_precipitation', 'f4'),
                   ('frozen_precipitation', 'f4'),
                   ('convective_precipitation', 'f4'),
                   ('rain_water_path', 'f4'),
                   ('cloud_water_path', 'f4'),
                   ('ice_water_path', 'f4'),
                   ('most_likely_precip', 'f4'),
                   ('1st_tertial', 'f4'),
                   ('2nd_tertial', 'f4'),
                   ('profile_temp_2m_index', 'i2')]
    pixel_types += [('profile_number', 'i2', n_species)]
    pixel_types += [('profile_scale', 'f4', n_species)]
    return pixel_types

SCAN_HEADER_TYPES_GPROF = [('latitude', 'f4'),
                           ('longitude', 'f4'),
                           ('altitude', 'f4'),
                           ('time', 'S14'),
                           ('spare', 'S2')]

def get_gprof_file(filename):
    """
    Get binary GPROF retrieval file matching database file.

    Args:
        filename: The filename of the training database file.


    Returns:
        The path of the corresponding binary GPROF file.
    """
    data = Path(filename).name.split(".")[2:4]
    print(data)
    exp = re.compile(f".*{data[0]}.*{data[1]}\.BIN")
    path = Path.home() / "Dendrite/UserAreas/Simon/GPROF"
    files = path.glob("**/*.BIN")
    match = [file for file in files if exp.match(file.name)]
    return match[0]


class GPROFBinaryFile:
    """
    Class to extract data from binary  GMI GPROF retrieval  files and store to
    NetCDF file.
    """
    def __init__(self, filename):
        """
        Open CSU binary file containing GPROF retrieval data.

        Args:
            filename(``pathlib.Path``): The file to open.
        """
        self.filename = filename
        self.header = np.memmap(filename,
                                dtype=HEADER_TYPES_GPROF,
                                mode="r",
                                shape=(1,))
        self.n_scans = self.header["num_scans"][0]
        self.n_pixels = self.header["num_pixels"][0]
        self.n_species = self.header["num_species"][0]
        self.n_layers = self.header["num_layers"][0]
        self.n_temps = self.header["num_temps"][0]
        self.n_profiles = self.header["num_profiles"][0]

        self.pixel_types = get_pixel_types_gprof(self.n_species)
        self.header_size = sum(np.dtype(t[1]).itemsize for t in HEADER_TYPES_GPROF)

        self.profile_info_types=get_profile_types_gprof(self.n_species,
                                                        self.n_temps,
                                                        self.n_layers,
                                                        self.n_profiles)
        self.profile_info = np.memmap(filename,
                                      self.profile_info_types,
                                      offset=self.header_size,
                                      shape=(1,))

        self.scan_header_size = np.dtype(SCAN_HEADER_TYPES_GPROF).itemsize
        self.pixel_size = np.dtype(self.pixel_types).itemsize
        self.scan_size = int(self.scan_header_size) + self.n_pixels * int(self.pixel_size)
        self.profile_info_size = np.dtype(self.profile_info_types).itemsize
        self.total_size = int(self.header_size) + self.n_scans * self.scan_size

    def __getitem__(self, indices):
        """
        Return retrieval result for pixel.

        Args:
            indices: Tuple (i, j) containing scan index i and pixel
                index j.

        Return:
            Numpy array containing the pixel data.
        """
        i, j = indices
        offset = self.header_size + self.profile_info_size
        offset += i * self.scan_size
        offset += self.scan_header_size + j * self.pixel_size
        return np.memmap(self.filename,
                         self.pixel_types,
                         offset=offset,
                         shape=(1,))[0]


    def _create_gprof_group(self, file):
        """
        Add gprof group to NetCDf file.

        Args:
            ``netCDF4.Dataset`` to which to add a 'gprof' group.

        """
        g = file.createGroup("gprof")
        g.createVariable("surface_precipitation", "f4", dimensions=("samples",))
        g.createVariable("convective_precipitation", "f4", dimensions=("samples",))
        g.createVariable("1st_tertial", "f4", dimensions=("samples",))
        g.createVariable("2nd_tertial", "f4", dimensions=("samples",))
        g.createVariable("probability_of_precipitation", "f4", dimensions=("samples",))

    def add_to_file(self, file, nx, ny):
        """
        Add retrieval result to file.

        Args:
            file(``netCDF4.Dataset``): The netCDF4 file handle to which to add
                the data.
            nx(``numpy.ndarray``): The scan indices of the retrieval results to
                add to the file.
            ny(``numpy.ndarray``): The pixel indices of the retrieval results to
                add to the file.
        """
        if not "gprof" in file.groups:
            self._create_gprof_group(file)

        g = file["gprof"]
        v_sp = g["surface_precipitation"]
        v_cp = g["convective_precipitation"]
        v_1t = g["1st_tertial"]
        v_2t = g["2nd_tertial"]
        v_pop = g["probability_of_precipitation"]

        n = len(nx)
        n_samples = file.dimensions["samples"].size
        indices = (n_samples - n, n_samples)
        for i, (x, y) in enumerate(zip(nx, ny)):
            d = self[x, y]
            v_sp[i] = d["surface_precipitation"]
            v_cp[i] = d["convective_precipitation"]
            v_1t[i] = d["1st_tertial"]
            v_2t[i] = d["2nd_tertial"]
            v_pop[i] = d["probability_of_precipitation"]
