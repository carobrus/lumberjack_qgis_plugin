import os
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
TEXTURES_SUFFIX = "_text.tif"
IMAGE_METADATA_SUFFIX = "_MTL.txt"


class Feature:
    # Parent class which defines a common interface for all features
    def __init__(self):
        self.feature_names = []


    def execute(self, file_in):
        raise NotImplementedError("Subclasses mut override execute()")


class AlgebraFeature(Feature):
    def __init__(self):
        super().__init__()
        self.feature_names = ["mean", "std", "slope", "intercept"]


    def get_file_name(self, path, base_name):
        return os.path.join(path, "{}_sr{}".format(base_name, ALGEBRA_SUFFIX))


    def execute(self, file_in):
        file_out = file_in[:-11]
        bands_algebra.generate_algebra_file(file_in, file_out)


class FilterFeature(Feature):
    def __init__(self):
        super().__init__()
        self.feature_names = []


    def get_file_name(self, path, base_name):
        return os.path.join(path, "{}_sr{}".format(base_name, FILTER_SUFFIX))


    def execute(self, file_in):
        file_out = file_out = file_in[:-11]
        band_count = filters.generate_filter_file(
            file_input=file_in, file_output_median=file_out)
        if (not self.feature_names):
            self.feature_names = (
                ["median_filt_band{}".format(i) for i in range(1, band_count+1)])


class FilterGaussFeature(Feature):
    def __init__(self):
        super().__init__()
        self.feature_names = []


    def get_file_name(self, path, base_name):
        return os.path.join(path, "{}_sr{}".format(base_name, GAUSS_SUFFIX))


    def execute(self, file_in):
        file_out = file_in[:-11]
        band_count = filters.generate_filter_file(
            file_input=file_in, file_output_gaussian=file_out)
        if (not self.feature_names):
            self.feature_names = (
                ["gauss_filt_band{}".format(i) for i in range(1, band_count+1)])


class NdviFeature(Feature):
    def __init__(self):
        super().__init__()
        self.feature_names = ["ndvi"]


    def get_file_name(self, path, base_name):
        return os.path.join(path, "{}_sr{}".format(base_name, NDVI_SUFFIX))


    def execute(self, file_in):
        file_out = file_in[:-11]
        ndvi.generate_ndvi_file(file_in, file_out)


class DayFeature(Feature):
    def __init__(self):
        super().__init__()
        self.feature_names = ["day_normalized", "day_transform"]


    def get_file_name(self, path, base_name):
        return os.path.join(path, "{}_sr{}".format(base_name, DAY_SUFFIX))


    def execute(self, file_in):
        file_out = file_in[:-11]
        file_name_metadata = "{}{}".format(
            file_in[:-14], IMAGE_METADATA_SUFFIX)
        date = self.get_date_from_metadata(file_name_metadata)
        row = int(self.get_row_from_metadata(file_name_metadata))
        number_of_day = self.transform_day(date, row)
        number_of_day_normalized = number_of_day / 366
        number_of_day_transform = math.sin(number_of_day_normalized * math.pi)

        # Create a new file
        dataset = gdal.Open(file_in, gdal.GA_ReadOnly)
        driver = gdal.GetDriverByName('GTiff')
        output_dataset = driver.Create(
            file_out, dataset.RasterXSize, dataset.RasterYSize,
            2, gdal.GDT_Float32)
        output_dataset.SetProjection(dataset.GetProjectionRef())
        output_dataset.SetGeoTransform(dataset.GetGeoTransform())

        # Write a band with the day normalized for each pixel
        band = np.full(
            (dataset.RasterYSize, dataset.RasterXSize),
            number_of_day_normalized)
        outband = output_dataset.GetRasterBand(1)
        outband.WriteArray(band)

        # Write a band with the day transformed for each pixel
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
        # If the image is from the northern hemisphere
        if (row < 60):
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


class TextureFeature(Feature):
    def __init__(self):
        super().__init__()
        self.feature_names = []


    def get_file_name(self, path, base_name):
        return os.path.join(path, "{}{}".format(base_name, TEXTURES_SUFFIX))


    def execute(self, file_in):
        if (not self.feature_names):
            dataset = gdal.Open(file_in, gdal.GA_ReadOnly)
            self.feature_names = (
                [dataset.GetRasterBand(i).GetDescription() for i in range(1, dataset.RasterCount+1)])


class DemTextureFeature(Feature):
    def __init__(self):
        super().__init__()
        self.feature_names = []


    def get_file_name(self, path, base_name):
        dir_dem_text = os.path.split(path)[0]
        for file in os.listdir(dir_dem_text):
            if file.endswith("_text.tif"):
                return os.path.join(dir_dem_text, file)


    def execute(self, file_in):
        if (not self.feature_names):
            dir_dem_text = os.path.split(os.path.split(file_in)[0])[0]
            for file in os.listdir(dir_dem_text):
                if file.endswith("_text.tif"):
                    file_dem_text = os.path.join(dir_dem_text, file)

                    dataset = gdal.Open(file_dem_text, gdal.GA_ReadOnly)
                    self.feature_names = (
                        ["dem-{}".format(dataset.GetRasterBand(i).GetDescription()) for i in range(1, dataset.RasterCount+1)])
