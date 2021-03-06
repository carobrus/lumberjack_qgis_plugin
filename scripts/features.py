import os
import time
import datetime
import math
import numpy as np
from osgeo import gdal

from . import bands_algebra
from . import filters
from . import ndvi
from .. import Lumberjack


class Feature:
    # Parent class which defines a common interface for all features
    def __init__(self):
        self.feature_names = []


    def get_file_name(self, image):
        raise NotImplementedError("Subclasses must override get_file_name()")


    def execute(self, file_in, image):
        raise NotImplementedError("Subclasses must override execute()")


class AlgebraFeature(Feature):
    SUFFIX = ""

    def __init__(self, suffix):
        super().__init__()
        AlgebraFeature.SUFFIX = suffix
        self.feature_names = ["mean", "std", "slope", "intercept"]


    def get_file_name(self, image):
        return os.path.join(image.path, "{}{}".format(image.base_name, AlgebraFeature.SUFFIX))


    def execute(self, file_in, image):
        file_out = self.get_file_name(image)
        bands_algebra.generate_algebra_file(file_in, file_out)


class FilterFeature(Feature):
    SUFFIX = ""

    def __init__(self, suffix):
        super().__init__()
        FilterFeature.SUFFIX = suffix
        self.feature_names = []


    def get_file_name(self, image):
        return os.path.join(image.path, "{}{}".format(image.base_name, FilterFeature.SUFFIX))


    def execute(self, file_in, image):
        file_out = self.get_file_name(image)
        band_count = filters.generate_filter_file(file_input=file_in, file_output_median=file_out)
        if (not self.feature_names):
            self.feature_names = (["median_band{}".format(i) for i in range(1, band_count+1)])


class FilterGaussFeature(Feature):
    SUFFIX = ""

    def __init__(self, suffix):
        super().__init__()
        FilterGaussFeature.SUFFIX = suffix
        self.feature_names = []


    def get_file_name(self, image):
        return os.path.join(image.path, "{}{}".format(image.base_name, FilterGaussFeature.SUFFIX))


    def execute(self, file_in, image):
        file_out = self.get_file_name(image)
        band_count = filters.generate_filter_file(file_input=file_in, file_output_gaussian=file_out)
        if (not self.feature_names):
            self.feature_names = (["gauss_band{}".format(i) for i in range(1, band_count+1)])


class NdviFeature(Feature):
    SUFFIX = ""

    def __init__(self, suffix):
        super().__init__()
        NdviFeature.SUFFIX = suffix
        self.feature_names = ["ndvi"]


    def get_file_name(self, image):
        return os.path.join(image.path, "{}{}".format(image.base_name, NdviFeature.SUFFIX))


    def execute(self, file_in, image):
        file_out = self.get_file_name(image)
        ndvi.generate_ndvi_file(file_in, file_out)


class DayFeature(Feature):
    SUFFIX = ""

    def __init__(self, suffix):
        super().__init__()
        DayFeature.SUFFIX = suffix
        self.feature_names = ["day_normalized", "day_transform"]


    def get_file_name(self, image):
        return os.path.join(image.path, "{}{}".format(image.base_name, DayFeature.SUFFIX))


    def execute(self, file_in, image):
        file_out = self.get_file_name(image)
        date = self.get_date_from_metadata(image.metadata_file)
        row = int(self.get_row_from_metadata(image.metadata_file))
        number_of_day = self.transform_day(date, row)
        number_of_day_normalized = number_of_day / 366
        number_of_day_transform = math.sin(number_of_day_normalized * math.pi)

        # Create a new file
        dataset = gdal.Open(file_in, gdal.GA_ReadOnly)
        driver = gdal.GetDriverByName('GTiff')
        output_dataset = driver.Create(file_out, dataset.RasterXSize, dataset.RasterYSize, 2, gdal.GDT_Float32)
        output_dataset.SetProjection(dataset.GetProjectionRef())
        output_dataset.SetGeoTransform(dataset.GetGeoTransform())

        # Write a band with the day normalized for each pixel
        band = np.full((dataset.RasterYSize, dataset.RasterXSize), number_of_day_normalized)
        outband = output_dataset.GetRasterBand(1)
        outband.SetDescription("day_normalized")
        outband.WriteArray(band)

        # Write a band with the day transformed for each pixel
        band = np.full((dataset.RasterYSize, dataset.RasterXSize), number_of_day_transform)
        outband = output_dataset.GetRasterBand(2)
        outband.SetDescription("day_transform")
        outband.WriteArray(band)


    def transform_day(self, date, row):
        year, month, day = date.split("-")
        year = int(year)
        month = int(month)
        day = int(day)
        number_of_day = (datetime.date(year, month, day) - datetime.date(year, 1, 1)).days + 1
        # If the image is from the northern hemisphere
        if (row < 60):
            number_of_day = (number_of_day + 182) % 365
        return number_of_day


    def get_date_from_metadata(self, file):
        with open(file, 'r') as f:
            for line in f.readlines():
                if "DATE_ACQUIRED =" in line:
                    l = line.split("=")
                    return l[1]


    def get_row_from_metadata(self, file):
        with open(file, 'r') as f:
            for line in f.readlines():
                if "WRS_ROW =" in line:
                    l = line.split("=")
                    return l[1]


class ImageFeature(Feature):
    def __init__(self, suffix):
        super().__init__()
        self.suffix = suffix
        self.feature_names = []


    def get_file_name(self, image):
       for file in os.listdir(image.path):
            if file.endswith(self.suffix):
                return os.path.join(image.path, file)


    def execute(self, file_in, image):
        if (not self.feature_names):
            file_features = self.get_file_name(image)
            dataset = gdal.Open(file_features, gdal.GA_ReadOnly)
            self.feature_names = ([dataset.GetRasterBand(i).GetDescription() for i in range(1, dataset.RasterCount+1)])


class PlaceFeature(Feature):
    SUFFIX = ""

    def __init__(self, suffix):
        super().__init__()
        PlaceFeature.SUFFIX = suffix
        self.feature_names = []


    def get_file_name(self, image):
        dir_dem_text = os.path.split(image.path)[0]
        for file in os.listdir(dir_dem_text):
            if file.endswith(PlaceFeature.SUFFIX):
                return os.path.join(dir_dem_text, file)


    def execute(self, file_in, image):
        if (not self.feature_names):
            file_dem_text = self.get_file_name(image)
            dataset = gdal.Open(file_dem_text, gdal.GA_ReadOnly)
            self.feature_names = (
                ["dem-{}".format(dataset.GetRasterBand(i).GetDescription()) for i in range(1, dataset.RasterCount+1)])
