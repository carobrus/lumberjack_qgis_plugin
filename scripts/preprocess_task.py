from qgis.core import (QgsApplication, QgsTask, QgsMessageLog, Qgis)
import os
import subprocess
import time
import datetime
from osgeo import gdal
from osgeo import ogr
import numpy as np
from .image import Image
from .place import Place
from .classifier import Classifier
from .. import Lumberjack


IMAGE_METADATA_SUFFIX = "MTL.txt"
EXTENSION_FILE_SUFFIX = "ext.tif"
DEM_TEXTURES_SUFFIX = "textures.tif"
TEXTURES_SUFFIX = "text.tif"
CROP_SUFFIX = "crop.tif"
MERGED_SUFFIX = "merged.tif"
SHAPEFILE_SUFFIX = "roi.shp"
BAND_TOTAL = 7


class PreProcessTask(QgsTask):

    def obtain_places(self, root_directory):
        places = []
        for place_directory in os.scandir(root_directory):
            if (place_directory.is_dir()):
                place = Place(place_directory.path)

                for image_directory_or_file in os.scandir(place.directory_path):
                    if (image_directory_or_file.is_dir()):
                        image_directory = str(image_directory_or_file.path)
                        image = Image(image_directory)
                        for image_subfile in os.scandir(image_directory):
                            image_subfile_path = str(image_subfile.path)
                            if (image_subfile_path[-(len(IMAGE_METADATA_SUFFIX)):] == IMAGE_METADATA_SUFFIX):
                                image.base_name = image_subfile_path[-48:-8]
                            elif (image_subfile_path[-(len(TEXTURES_SUFFIX)):] == TEXTURES_SUFFIX):
                                image.extra_features = image_subfile_path
                        place.images.append(image)
                    elif (image_directory_or_file.is_file()):
                        file_path = str(image_directory_or_file.path)
                        if (file_path[-(len(EXTENSION_FILE_SUFFIX)):] == EXTENSION_FILE_SUFFIX):
                            place.extension_file_path = file_path
                        elif (file_path[-(len(DEM_TEXTURES_SUFFIX)):] == DEM_TEXTURES_SUFFIX):
                            place.dem_textures_file_path = file_path
                        elif (file_path[-(len(SHAPEFILE_SUFFIX)):] == SHAPEFILE_SUFFIX):
                            place.vector_file_path = file_path
                places.append(place)
        return places


    def calculate_extension(self, extension_file_path):
        extension_dataset = gdal.Open(extension_file_path, gdal.GA_ReadOnly)
        geoTransform = extension_dataset.GetGeoTransform()
        minx = geoTransform[0]
        maxy = geoTransform[3]
        maxx = minx + geoTransform[1] * extension_dataset.RasterXSize
        miny = maxy + geoTransform[5] * extension_dataset.RasterYSize
        return minx, maxy, maxx, miny


    def crop_images(self, file_name_band, file_name_crop, minx, maxy, maxx, miny):
        # Crops all images according to the extension.
        for i in range(1, BAND_TOTAL+1):
            # Crop image to extension
            command_translate = "gdal_translate -projwin {} {} {} {} -ot Int16 -of GTiff \"{}\" \"{}\""
            subprocess.call(command_translate.format(
                minx, maxy, maxx, miny, file_name_band.format(i),
                file_name_crop.format(i)), stdout=open(os.devnull, 'wb'),
                shell=True)


    def merge_images(self, files, file_name_merged, bands_amount, data_type):
        bands_acum = 0
        output_dataset = None
        print("File Name Merged: " + file_name_merged)

        dataset = gdal.Open(files[0], gdal.GA_ReadOnly)
        driver = gdal.GetDriverByName('GTiff')
        output_dataset = driver.Create(
            file_name_merged, dataset.RasterXSize, dataset.RasterYSize,
            bands_amount, data_type)
        output_dataset.SetGeoTransform(dataset.GetGeoTransform())
        output_dataset.SetProjection(dataset.GetProjection())
        dataset = None

        for i, file_path in enumerate(files):
            dataset = gdal.Open(file_path, gdal.GA_ReadOnly)
            for j in range(dataset.RasterCount):
                bands_acum += 1
                band_read = dataset.GetRasterBand(j+1).ReadAsArray()
                outband = output_dataset.GetRasterBand(bands_acum)
                outband.WriteArray(band_read)


    def calculate_total_features(self, files):
        total = 0
        for file in files:
            dataset = gdal.Open(file, gdal.GA_ReadOnly)
            total += dataset.RasterCount
        return total


    def pre_process_images(self, places):
        for place in places:
            minx, maxy, maxx, miny = self.calculate_extension(
                place.extension_file_path)
            for image in place.images:
                # image represent each landsat image (a folder with the bands)
                print("Landsat image directory: {}".format(image.path))

                file_name_band = "{}/{}_sr_band{}.tif".format(
                    image.path, image.base_name, "{}")
                file_name_crop = "{}/{}_sr_band{}_{}".format(
                    image.path, image.base_name, "{}", CROP_SUFFIX)
                file_name_merged = "{}/{}_sr_{}".format(
                    image.path, image.base_name, MERGED_SUFFIX)

                self.crop_images(
                    file_name_band, file_name_crop, minx, maxy, maxx, miny)

                files_to_merge = []
                for i in range(1, BAND_TOTAL+1):
                    files_to_merge.append(file_name_crop.format(i))
                self.merge_images(files_to_merge, file_name_merged, BAND_TOTAL, gdal.GDT_Int16)
                for file in files_to_merge:
                    if os.path.exists(file):
                        os.remove(file)

                for feature in self.features:
                    feature.execute(file_name_merged)


    def __init__(self, description, task):
        super().__init__(description, task)

    def run(self):
        """Here you implement your heavy lifting.
        Should periodically test for isCanceled() to gracefully abort.
        This method MUST return True or False.
        Raising exceptions will crash QGIS, so we handle them
        internally and raise them in self.finished
        """
        raise NotImplementedError("Subclasses mut override run()")


    def finished(self, result):
        """
        This function is automatically called when the task has completed
            (successfully or not).
        You implement finished() to do whatever follow-up stuff should happen
            after the task is complete. finished is always called from the main
            thread, so it's safe to do GUI operations and raise Python
            exceptions here.
        result is the return value from self.run.
        """
        raise NotImplementedError("Subclasses mut override finished()")


    def cancel(self):
        QgsMessageLog.logMessage(
            'Task "{name}" was canceled'.format(
                name=self.description()),
            Lumberjack.MESSAGE_CATEGORY, Qgis.Info)
        super().cancel()
