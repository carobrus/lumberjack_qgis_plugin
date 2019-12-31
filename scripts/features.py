import time
import datetime
import math
import numpy as np
from osgeo import gdal

from . import bands_algebra
from . import filters
from . import ndvi

ALGEBRA_SUFFIX = "_alge.tif"
FILTER_SUFFIX = "_filt.tif"
GAUSS_SUFFIX = "_gaus.tif"
NDVI_SUFFIX =  "_ndvi.tif"
DAY_SUFFIX = "_day.tif"
IMAGE_METADATA_SUFFIX = "_MTL.txt"


class Feature:
    def __init__(self):
        self.file_format = ""

    def execute(self, file_in):
        raise NotImplementedError("Subclasses mut override execute()")


class AlgebraFeature(Feature):
    def __init__(self):
        super().__init__()
        self.file_format = "{}{}".format("{}", ALGEBRA_SUFFIX)

    def execute(self, file_in):
        file_out = self.file_format.format(file_in[:-4])
        bands_algebra.generate_algebra_file(file_in, file_out)


class FilterFeature(Feature):
    def __init__(self):
        super().__init__()
        self.file_format = "{}{}".format("{}", FILTER_SUFFIX)

    def execute(self, file_in):
        file_out = self.file_format.format(file_in[:-4])
        filters.generate_filter_file(
            file_input=file_in, file_output_median=file_out)


class FilterGaussFeature(Feature):
    def __init__(self):
        super().__init__()
        self.file_format = "{}{}".format("{}", GAUSS_SUFFIX)

    def execute(self, file_in):
        file_out = self.file_format.format(file_in[:-4])
        filters.generate_filter_file(
            file_input=file_in, file_output_gaussian=file_out)


class NdviFeature(Feature):
    def __init__(self):
        super().__init__()
        self.file_format = "{}{}".format("{}", NDVI_SUFFIX)

    def execute(self, file_in):
        file_out = self.file_format.format(file_in[:-4])
        ndvi.generate_ndvi_file(file_in, file_out)


class DayFeature(Feature):
    def __init__(self):
        super().__init__()
        self.file_format = "{}{}".format("{}", DAY_SUFFIX)

    def execute(self, file_in):
        file_out = self.file_format.format(file_in[:-4])
        file_name_metadata = "{}{}".format(file_in[:-14], IMAGE_METADATA_SUFFIX)
        date = self.get_date_from_metadata(file_name_metadata)
        row = int(self.get_row_from_metadata(file_name_metadata))
        number_of_day = self.transform_day(date, row)
        number_of_day_normalized = number_of_day / 366
        number_of_day_transform = math.sin(number_of_day_normalized * math.pi)

        dataset = gdal.Open(file_in, gdal.GA_ReadOnly)
        driver = gdal.GetDriverByName('GTiff')
        output_dataset = driver.Create(
            file_out, dataset.RasterXSize, dataset.RasterYSize,
            2, gdal.GDT_Float32)
        output_dataset.SetProjection(dataset.GetProjectionRef())
        output_dataset.SetGeoTransform(dataset.GetGeoTransform())
        band = np.full(
            (dataset.RasterYSize, dataset.RasterXSize),
            number_of_day_normalized)
        outband = output_dataset.GetRasterBand(1)
        outband.WriteArray(band)
        band = np.full(
            (dataset.RasterYSize, dataset.RasterXSize),
            number_of_day_transform)
        outband = output_dataset.GetRasterBand(2)
        outband.WriteArray(band)

    def transform_day(self, date, row):
        year, month, day = date.split("-")
        year = int(year)
        month = int(month)
        day = int(day)
        number_of_day = (datetime.date(year, month, day) -
                         datetime.date(year, 1, 1)).days + 1
        if (row < 60): # If the image is from the northern hemisphere
            number_of_day = (number_of_day + 182) % 365
        return number_of_day

    def get_date_from_metadata(self, file):
        f = open(file, 'r')
        for line in f.readlines():
            if "DATE_ACQUIRED =" in line:
                l = line.split("=")
                return l[1]

    def get_row_from_metadata(self, file):
        f = open(file, 'r')
        for line in f.readlines():
            if "WRS_ROW =" in line:
                l = line.split("=")
                return l[1]


# class TextureFeature():
#     def __init__(self, file_out):
#         super().__init__()
#
#     def execute(file_in):
#         file_out = "{}{}".format(file_in[:-4], PERSONALIZED_SUFFIX)
