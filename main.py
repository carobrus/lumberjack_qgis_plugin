from qgis.core import (QgsApplication, QgsTask, QgsMessageLog, Qgis)
import os
import subprocess
import time
import datetime
import math
from osgeo import gdal
from osgeo import ogr
import numpy as np
from .image import Image
from .place import Place
from .classifier import Classifier
from . import bands_algebra
from . import filters
from . import ndvi
from . import threshold


MESSAGE_CATEGORY = 'Lumberjack'

IMAGE_METADATA_SUFFIX = "MTL.txt"
EXTENSION_FILE_SUFFIX = "ext.tif"
DEM_TEXTURES_SUFFIX = "textures.tif"
TEXTURES_SUFFIX = "text.tif"
CROP_SUFFIX = "crop.tif"
MERGED_SUFFIX = "merged.tif"
STACK_SUFFIX = "stack.csv"
SHAPEFILE_SUFFIX = "roi.shp"
PREDICTION_SUFFIX = "predic"
BAND_TOTAL = 7


class Main(QgsTask):
    MESSAGE_CATEGORY = 'Lumberjack'

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


    def merge_images(self, files, file_name_merged, bands_amount):
        bands_acum = 0
        output_dataset = None
        print("File Name Merged: " + file_name_merged)

        dataset = gdal.Open(files[0], gdal.GA_ReadOnly)
        driver = gdal.GetDriverByName('GTiff')
        output_dataset = driver.Create(
            file_name_merged, dataset.RasterXSize, dataset.RasterYSize,
            bands_amount, gdal.GDT_Int16)
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
                self.merge_images(files_to_merge, file_name_merged, BAND_TOTAL)
                for file in files_to_merge:
                    if os.path.exists(file):
                        os.remove(file)

                files = []
                files.append(file_name_merged)
                for feature in self.features:
                    feature.execute(file_name_merged)
                    files.append(feature.file_out)
                files.append(image.extra_features)
                files.append(place.dem_textures_file_path)

                file_name_stack = "{}/{}_sr_{}_{}".format(
                    image.path, image.base_name, "{}", STACK_SUFFIX)

                self.filter_features(
                    place.vector_file_path[:-4]+".tif", files, file_name_stack)

                for file in files:
                    if (file != image.extra_features)  and (file != place.dem_textures_file_path):
                        if os.path.exists(file):
                            os.remove(file)


    def rasterize_vector_files(self, places):
        for place in places:
            rasterized_vector_file = place.vector_file_path[:-4] + ".tif"
            print("Creating ROI: " + rasterized_vector_file)

            # Rasterize
            tiff_dataset = gdal.Open(
                place.extension_file_path, gdal.GA_ReadOnly)
            memory_driver = gdal.GetDriverByName('GTiff')
            if os.path.exists(rasterized_vector_file):
                os.remove(rasterized_vector_file)
            out_raster_ds = memory_driver.Create(
                rasterized_vector_file, tiff_dataset.RasterXSize,
                tiff_dataset.RasterYSize, 1, gdal.GDT_Byte)

            # Set the ROI image's projection and extent to the ones of the input
            out_raster_ds.SetProjection(tiff_dataset.GetProjectionRef())
            out_raster_ds.SetGeoTransform(tiff_dataset.GetGeoTransform())
            tiff_dataset = None

            # Fill output band with the 0 blank, no class label, value
            b = out_raster_ds.GetRasterBand(1)
            b.Fill(0)

            vector_dataset = ogr.Open(place.vector_file_path)
            layer = vector_dataset.GetLayerByIndex(0)
            # Rasterize the shapefile layer to our new dataset
            status = gdal.RasterizeLayer(
                out_raster_ds, [1], layer, None, None, [0],
                ['ALL_TOUCHED=TRUE', 'ATTRIBUTE=id'])

            # Close dataset
            out_raster_ds = None
            if status != 0:
                print("Error creating rasterized tiff")


    def __init__(self, description, task):
        super().__init__("Lumberjack execution", QgsTask.CanCancel)

    def run(self):
        """Here you implement your heavy lifting.
        Should periodically test for isCanceled() to gracefully abort.
        This method MUST return True or False.
        Raising exceptions will crash QGIS, so we handle them
        internally and raise them in self.finished
        """
        # try:
        #     QgsMessageLog.logMessage('Started task "{}"'.format(
        #         self.description()), MESSAGE_CATEGORY, Qgis.Info)
        #
        #     self.start_time_str = str(datetime.datetime.now())
        #     print("=" * 30 + self.start_time_str + "=" * 30)
        #     self.start_time = time.time()
        #
        #     places_training = self.obtain_places(self.training_directory)
        #
        #     self.rasterize_vector_files(places_training)
        #     self.pre_process_images(places_training)
        #
        #     # Create classifier and add samples to train
        #     classifier = Classifier()
        #     self.classes_training = self.check_classes(places_training)
        #     for place in places_training:
        #         for image in place.images:
        #             file_name_stack = "{}/{}_sr_{}_{}".format(
        #                 image.path, image.base_name, "{}", STACK_SUFFIX)
        #             classifier.add_training_samples(file_name_stack)
        #
        #     if self.isCanceled():
        #         return False
        #
        #     if (self.do_testing):
        #         places_testing = self.obtain_places(self.testing_directory)
        #         self.rasterize_vector_files(places_testing)
        #         self.pre_process_images(places_testing)
        #         self.classes_output = self.check_classes(places_testing)
        #         for place in places_testing:
        #             for image in place.images:
        #                 file_name_stack = "{}/{}_sr_{}_{}".format(
        #                     image.path, image.base_name, "{}", STACK_SUFFIX)
        #                 classifier.add_testing_samples(file_name_stack)
        #
        #     if self.isCanceled():
        #         return False
        #
        #     # Build forest of trees and calculate metrics
        #     self.metrics = classifier.fit_and_calculate_metrics(0.25)
        #
        #     if self.isCanceled():
        #         return False
        #
        #     if self.do_prediction:
        #         places_prediction = self.obtain_places(
        #             self.prediction_directory)
        #         self.pre_process_images(places_prediction)
        #         self.output_files = self.predict(
        #             places_prediction, classifier, self.start_time_str[:19])
        #
        #
        #     self.elapsed_time = time.time() - self.start_time
        #     print("Finished in {} seconds".format(str(self.elapsed_time)))
        #
        #     if self.isCanceled():
        #         return False
        #
        #     self.setProgress(100)
        #     return True
        #
        # except Exception as e:
        #     self.exception = e
        #     return False
        pass


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
        # if result:
        #     QgsMessageLog.logMessage(
        #         'Task "{name}" completed in {time} seconds\n' \
        #         'Training Directory: {td})'.format(
        #             name=self.description(),
        #             time=self.elapsed_time,
        #             td=self.training_directory),
        #         MESSAGE_CATEGORY, Qgis.Success)
        #
        #     self.li.notify_metrics(
        #         self.start_time_str, self.classes_training, self.classes_output,
        #         self.metrics, self.elapsed_time)
        #     self.li.notify_task(self.start_time_str, self.output_files)
        #
        # else:
        #     if self.exception is None:
        #         QgsMessageLog.logMessage(
        #             'Task "{name}" not successful but without '\
        #             'exception (probably the task was manually '\
        #             'canceled by the user)'.format(
        #                 name=self.description()),
        #             MESSAGE_CATEGORY, Qgis.Warning)
        #     else:
        #         QgsMessageLog.logMessage(
        #             'Task "{name}" Exception: {exception}'.format(
        #                 name=self.description(),
        #                 exception=self.exception),
        #             MESSAGE_CATEGORY, Qgis.Critical)
        #         raise self.exception
        pass


    def cancel(self):
        QgsMessageLog.logMessage(
            'Task "{name}" was canceled'.format(
                name=self.description()),
            MESSAGE_CATEGORY, Qgis.Info)
        super().cancel()


class PredictTask(Main):
    def predict(self, places, classifier, time_stamp):
        output_files = []
        for place in places:
            for image in place.images:
                stack_file_name = "{}/{}_sr_{}_{}".format(
                    image.path, image.base_name, "{}",STACK_SUFFIX)
                output_file = "{}/{}_sr_{}_{}.tif".format(
                    image.path, image.base_name, PREDICTION_SUFFIX,
                    time_stamp.replace(" ", "_").replace(":","-"))
                output_files.append(output_file)
                classifier.predict_an_image(stack_file_name, output_file)
        return output_files
