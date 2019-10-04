import time
import datetime
import math
import numpy as np
from osgeo import gdal

from . import bands_algebra
from . import filters
from . import ndvi

ALGEBRA_SUFFIX = "alge.tif"
FILTER_SUFFIX = "filt.tif"
GAUSS_SUFFIX = "gaus.tif"
NDVI_SUFFIX =  "ndvi.tif"
DAY_SUFFIX = "day.tif"
IMAGE_METADATA_SUFFIX = "MTL.txt"


class Feature:
    def __init__(self):
        self.file_format = ""

    def execute(self, file_in):
        raise NotImplementedError("Subclasses mut override execute()")


class AlgebraFeature(Feature):
    def __init__(self):
        super().__init__()
        self.file_format = "{}_{}".format("{}", ALGEBRA_SUFFIX)

    def execute(self, file_in):
        file_out = self.file_format.format(file_in[:-4])
        bands_algebra.generate_algebra_file(file_in, file_out)


class FilterFeature(Feature):
    def __init__(self):
        super().__init__()
        self.file_format = "{}_{}".format("{}", FILTER_SUFFIX)

    def execute(self, file_in):
        file_out = self.file_format.format(file_in[:-4])
        filters.generate_filter_file(
            file_input=file_in, file_output_median=file_out)


class FilterGaussFeature(Feature):
    def __init__(self):
        super().__init__()
        self.file_format = "{}_{}".format("{}", GAUSS_SUFFIX)

    def execute(self, file_in):
        file_out = self.file_format.format(file_in[:-4])
        filters.generate_filter_file(
            file_input=file_in, file_output_gaussian=file_out)


class NdviFeature(Feature):
    def __init__(self):
        super().__init__()
        self.file_format = "{}_{}".format("{}", NDVI_SUFFIX)

    def execute(self, file_in):
        file_out = self.file_format.format(file_in[:-4])
        ndvi.generate_ndvi_file(file_in, file_out)


class DayFeature(Feature):
    def __init__(self):
        super().__init__()
        self.file_format = "{}_{}".format("{}", DAY_SUFFIX)

    def execute(self, file_in):
        file_out = self.file_format.format(file_in[:-4])
        file_name_metadata = "{}_{}".format(file_in[:-14], IMAGE_METADATA_SUFFIX)
        date = self.get_date_from_metadata(file_name_metadata)
        number_of_day = self.transform_day(date)
        number_of_day_normalized = number_of_day / 366
        number_of_day_transform = math.sin(number_of_day_normalized * math.pi)

        dataset = gdal.Open(file_in, gdal.GA_ReadOnly)
        driver = gdal.GetDriverByName('GTiff')
        output_dataset = driver.Create(
            file_out, dataset.RasterXSize, dataset.RasterYSize,
            2, gdal.GDT_Int16)
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

    def transform_day(self, date):
        year, month, day = date.split("-")
        year = int(year)
        month = int(month)
        day = int(day)
        number_of_day = (datetime.date(year, month, day) -
                         datetime.date(year, 1, 1)).days + 1
        return number_of_day

    def get_date_from_metadata(self, file):
        f = open(file, 'r')
        for line in f.readlines():
            if "DATE_ACQUIRED =" in line:
                l = line.split("=")
                return l[1]


# class TextureFeature():
#     def __init__(self, file_out):
#         super().__init__()
#
#     def execute(file_in):
#         file_out = "{}_{}".format(file_in[:-4], PERSONALIZED_SUFFIX)
