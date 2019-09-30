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
ALGEBRA_SUFFIX = "alge.tif"
NDVI_SUFFIX =  "ndvi.tif"
FILTER_SUFFIX = "filt.tif"
GAUSS_SUFFIX = "gaus.tif"
CROP_SUFFIX = "crop.tif"
MERGED_SUFFIX = "merged.tif"
STACK_SUFFIX = "stack.tif"
TEXTURES_SUFFIX = "text.tif"
SHAPEFILE_SUFFIX = "roi.shp"
BAND_TOTAL = 7


class Main(QgsTask):

    def obtain_places(self, root_directory):
        places = []
        for place_directory in os.scandir(root_directory):
            if (place_directory.is_dir()):
                place = Place(place_directory.path)

                for image_directory_or_file in os.scandir(place.directory_path):
                    if (image_directory_or_file.is_dir()):
                        image_directory = str(image_directory_or_file.path)
                        for image_subfile in os.scandir(image_directory):
                            image_subfile_path = str(image_subfile.path)
                            if (image_subfile_path[-(len(IMAGE_METADATA_SUFFIX)):] == IMAGE_METADATA_SUFFIX):
                                base_name = image_subfile_path[-48:-8]
                        place.images.append(Image(image_directory, base_name))
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


    def crop_images(self, places):
        """
        Crops all images in the directory according to the extension file.
        Adds "crop" to the filename. It merges all the cropped images and
            creates a new file with the "merged" suffix.
        """
        for place in places:
            # Get Extension
            extension_dataset = gdal.Open(place.extension_file_path, gdal.GA_ReadOnly)
            geoTransform = extension_dataset.GetGeoTransform()
            minx = geoTransform[0]
            maxy = geoTransform[3]
            maxx = minx + geoTransform[1] * extension_dataset.RasterXSize
            miny = maxy + geoTransform[5] * extension_dataset.RasterYSize

            # For each image in a place
            for image in place.images:
                outRaster = None
                outband = None
                print("Image dir: {}".format(image.path))
                for i in range(1, BAND_TOTAL+1):
                    file_name_band = "{}/{}_sr_band{}.tif".format(image.path, image.base_name, i)
                    file_name_crop = "{}/{}_sr_band{}_{}.tif".format(image.path, image.base_name, i, CROP_SUFFIX)
                    # Crop image to extension
                    print("Cropping tiff file: {}_sr_band{}.tif".format(image.base_name, i))
                    command_translate = "gdal_translate -projwin {} {} {} {} -ot Int16 -of GTiff \"{}\" \"{}\""
                    subprocess.call(command_translate.format(minx, maxy, maxx, miny, file_name_band, file_name_crop), stdout=open(os.devnull, 'wb'), shell=True)
        # TODO: Remove cropped files after merged


    def merge_images(self, places):
        for place in places:
            # For each image in a place
            for image in place.images:
                merged_file_name = "{}/{}_sr_{}".format(image.path, image.base_name, MERGED_SUFFIX)
                # if os.path.exists(merged_file_name):
                #     os.remove(merged_file_name)

                for i in range(1, BAND_TOTAL+1):
                    file = "{}/{}_sr_band{}_{}.tif".format(image.path, image.base_name, i, CROP_SUFFIX)
                    dataset = gdal.Open(file, gdal.GA_ReadOnly)
                    if i == 1:
                        driver = gdal.GetDriverByName('GTiff')
                        out_raster = driver.Create(merged_file_name, dataset.RasterXSize, dataset.RasterYSize, BAND_TOTAL, gdal.GDT_Int16)
                        out_raster.SetGeoTransform(dataset.GetGeoTransform())
                        out_raster.SetProjection(dataset.GetProjection())
                    band_cropped = dataset.GetRasterBand(1).ReadAsArray()
                    outband = out_raster.GetRasterBand(i)
                    outband.WriteArray(band_cropped)
                # print ("Creating file: " + merged_file_name)


    def calculate_features(self, places, do_algebra, do_filters, do_ndvi):
        for place in places:
            for image in place.images:
                merged_file_name = "{}/{}_sr_{}".format(image.path, image.base_name, MERGED_SUFFIX)
                print("Generating features to file: {}".format(merged_file_name))
                if do_algebra:
                    bands_algebra.generate_algebra_file(merged_file_name, "{}_{}".format(merged_file_name[:-4], ALGEBRA_SUFFIX))
                if do_ndvi:
                    ndvi.generate_ndvi_file(merged_file_name, "{}_{}".format(merged_file_name[:-4], NDVI_SUFFIX))
                if do_filters:
                    filters.generate_filter_file(merged_file_name, "{}_{}".format(merged_file_name[:-4], FILTER_SUFFIX), "{}_{}".format(merged_file_name[:-4], GAUSS_SUFFIX))

    def stack(self, file_to_stack, output_dataset, band_num):
        dataset = gdal.Open(file_to_stack, gdal.GA_ReadOnly)
        for band_number in range(dataset.RasterCount):
            band_num += 1
            band = dataset.GetRasterBand(band_number + 1)
            outband = output_dataset.GetRasterBand(band_num)
            outband.WriteArray(band.ReadAsArray())
        return band_num

    def stack_features(self, places, do_algebra, do_filters, do_ndvi, do_textures, do_dem):
        features_total = BAND_TOTAL
        if do_algebra:
            features_total += 4
        if do_filters:
            features_total += 14
        if do_ndvi:
            features_total += 1
        if do_textures:
            features_total += 35
        if do_dem:
            features_total += 7

        for place in places:
            for image in place.images:
                merged_file_name = "{}/{}_sr_{}".format(image.path, image.base_name, MERGED_SUFFIX)

                # Create the image that's going to stack all the features
                stack_file_name = "{}/{}_sr_{}".format(image.path, image.base_name, STACK_SUFFIX)
                print("Creating file: {}".format(stack_file_name))

                outband = None
                out_raster_ds = None
                dataset = gdal.Open(merged_file_name, gdal.GA_ReadOnly)
                memory_driver = gdal.GetDriverByName('GTiff')
                if os.path.exists(stack_file_name):
                    os.remove(stack_file_name)
                out_raster_ds = memory_driver.Create(stack_file_name, dataset.RasterXSize, dataset.RasterYSize, features_total, gdal.GDT_Float32)
                out_raster_ds.SetProjection(dataset.GetProjectionRef())
                out_raster_ds.SetGeoTransform(dataset.GetGeoTransform())

                band_num = 0
                # Add merged file bands
                for band_number in range(dataset.RasterCount):
                    band_num += 1
                    band = dataset.GetRasterBand(band_number + 1)
                    outband = out_raster_ds.GetRasterBand(band_num)
                    outband.WriteArray(band.ReadAsArray())

                if do_algebra:
                    algebra_file_name = "{}_{}".format(merged_file_name[:-4], ALGEBRA_SUFFIX)
                    band_num = self.stack(algebra_file_name, out_raster_ds, band_num)

                if do_filters:
                    filter_file_name = "{}_{}".format(merged_file_name[:-4], FILTER_SUFFIX)
                    gauss_file_name = "{}_{}".format(merged_file_name[:-4], GAUSS_SUFFIX)
                    band_num = self.stack(filter_file_name, out_raster_ds, band_num)
                    band_num = self.stack(gauss_file_name, out_raster_ds, band_num)

                if do_ndvi:
                    ndvi_file_name = "{}_{}".format(merged_file_name[:-4], NDVI_SUFFIX)
                    band_num = self.stack(ndvi_file_name, out_raster_ds, band_num)

                if do_textures:
                    textures_file_name = "{}/{}_{}".format(image.path, image.base_name, TEXTURES_SUFFIX)
                    band_num = self.stack(textures_file_name, out_raster_ds, band_num)

                if do_dem:
                    band_num = self.stack(place.dem_textures_file_path, out_raster_ds, band_num)
                    metadata_file_name = "{}/{}_{}".format(image.path, image.base_name, IMAGE_METADATA_SUFFIX)
                    date = self.get_date_from_metadata(metadata_file_name)
                    number_of_day = self.transform_day(date)
                    number_of_day_normalized = number_of_day / 366
                    number_of_day_transform = math.sin(number_of_day_normalized * math.pi)
                    band_num += 1
                    band = np.full((dataset.RasterYSize, dataset.RasterXSize), number_of_day_normalized)
                    outband = out_raster_ds.GetRasterBand(band_num)
                    outband.WriteArray(band)
                    band_num += 1
                    band = np.full((dataset.RasterYSize, dataset.RasterXSize), number_of_day_transform)
                    outband = out_raster_ds.GetRasterBand(band_num)
                    outband.WriteArray(band)

                outband.FlushCache()
                out_raster_ds = None

    def transform_day(self, date):
        year, month, day = date.split("-")
        year = int(year)
        month = int(month)
        day = int(day)
        number_of_day = (datetime.date(year, month, day) - datetime.date(year, 1, 1)).days + 1
        return number_of_day

    def get_date_from_metadata(self, file):
        f = open(file, 'r')
        for line in f.readlines():
            if "DATE_ACQUIRED =" in line:
                l = line.split("=")
                return l[1]

    def rasterize_files(self, places):
        for place in places:
            rasterized_vector_file = place.vector_file_path[:-4] + ".tif"
            print("Creating ROI: " + rasterized_vector_file)

            # Rasterize
            tiff_dataset = gdal.Open(place.extension_file_path, gdal.GA_ReadOnly)
            memory_driver = gdal.GetDriverByName('GTiff')
            if os.path.exists(rasterized_vector_file):
                os.remove(rasterized_vector_file)
            out_raster_ds = memory_driver.Create(rasterized_vector_file, tiff_dataset.RasterXSize, tiff_dataset.RasterYSize, 1, gdal.GDT_Byte)

            # Set the ROI image's projection and extent to input raster's projection and extent
            out_raster_ds.SetProjection(tiff_dataset.GetProjectionRef())
            out_raster_ds.SetGeoTransform(tiff_dataset.GetGeoTransform())
            tiff_dataset = None

            # Fill output band with the 0 blank, no class label, value
            b = out_raster_ds.GetRasterBand(1)
            b.Fill(0)

            vector_dataset = ogr.Open(place.vector_file_path)
            layer = vector_dataset.GetLayerByIndex(0)
            # Rasterize the shapefile layer to our new dataset
            status = gdal.RasterizeLayer(out_raster_ds, [1], layer, None, None,
                                         [0], ['ALL_TOUCHED=TRUE', 'ATTRIBUTE=id'])

            # Close dataset
            out_raster_ds = None

            if status != 0:
                print("Error creating rasterized tiff")
            else:
                print("Rasterize tiff created")


    def add_samples(self, place, classifier, rasterized_vector_file, do_training):
        for image in place.images:
            stack_file_name = "{}/{}_sr_{}".format(image.path, image.base_name, STACK_SUFFIX)
            if do_training:
                classifier.add_training_samples(stack_file_name, rasterized_vector_file)
            else:
                classifier.add_test_samples(stack_file_name, rasterized_vector_file)


    def check_classes(self, places):
        output = []
        for place in places:
            rasterized_vector_file = place.vector_file_path[:-4] + ".tif"
            roi_ds = gdal.Open(rasterized_vector_file, gdal.GA_ReadOnly)
            roi = roi_ds.GetRasterBand(1).ReadAsArray().astype(np.uint8)

            classes = np.unique(roi)
            # Iterate over all class labels in the ROI image, printing out some information
            for c in classes:
                print('Class {c} contains {n} pixels'.format(c=c, n=(roi == c).sum()))
                output.append('Class {c} contains {n} pixels'.format(c=c, n=(roi == c).sum()))

            # Find how many non-zero entries there are
            n_samples = (roi > 0).sum()
            print('There are {n} samples'.format(n=n_samples))
            output.append('There are {n} samples'.format(n=n_samples))

        return output

    def predict(self, places, classifier, prediction_result_img):
        for place in places:
            for image in place.images:
                stack_file_name = "{}/{}_sr_{}".format(image.path, image.base_name, STACK_SUFFIX)
                classifier.predict_an_image(stack_file_name, prediction_result_img)


    # def calculate_threshold(self):
    #     return threshold.calculate_threshold()

    def pre_process_images(self, places):
        # Files to be cropped according the extension_file (all layers to be cropped and merged)
        self.crop_images(places)
        self.merge_images(places)
        self.calculate_features(places, self.do_algebra, self.do_filters, self.do_ndvi)
        self.stack_features(places, self.do_algebra, self.do_filters,
                            self.do_ndvi, self.do_textures, self.do_dem)


    def __init__(self, training_directory, do_algebra, do_filters, do_ndvi,
                 do_textures, do_dem, do_testing, testing_directory,
                 do_prediction, prediction_directory, output_file,
                 lumberjack_instance):
        super().__init__("Lumberjack execution", QgsTask.CanCancel)
        self.training_directory = training_directory
        self.do_algebra = do_algebra
        self.do_filters = do_filters
        self.do_ndvi = do_ndvi
        self.do_textures = do_textures
        self.do_dem = do_dem
        self.do_testing = do_testing
        self.testing_directory = testing_directory
        self.do_prediction = do_prediction
        self.prediction_directory = prediction_directory
        self.output_file = output_file
        self.exception = None
        self.li = lumberjack_instance

    def run(self):
        """Here you implement your heavy lifting.
        Should periodically test for isCanceled() to gracefully abort.
        This method MUST return True or False.
        Raising exceptions will crash QGIS, so we handle them
        internally and raise them in self.finished
        """
        try:
            QgsMessageLog.logMessage('Started task "{}"'.format(self.description()), MESSAGE_CATEGORY, Qgis.Info)
            self.setProgress(0)

            self.start_time_str = str(datetime.datetime.now())
            print("============================= " + self.start_time_str + " =============================")
            self.start_time = time.time()

            places_training = self.obtain_places(self.training_directory)
            self.pre_process_images(places_training)

            # Create classifier and add samples to train
            classifier = Classifier()
            self.rasterize_files(places_training)
            self.classes_training = self.check_classes(places_training)
            for place in places_training:
                self.add_samples(place, classifier, place.vector_file_path[:-4] + ".tif", True)

            self.setProgress(30)
            if self.isCanceled():
                return False

            self.classes_output = None
            if (self.do_testing):
                places_testing = self.obtain_places(self.testing_directory)
                self.pre_process_images(places_testing)
                self.rasterize_files(places_testing)
                self.classes_output = self.check_classes(places_testing)
                for place in places_testing:
                    # self.check_classes(rasterized_vector_file)
                    self.add_samples(place, classifier,  place.vector_file_path[:-4] + ".tif", False)

            self.setProgress(60)
            if self.isCanceled():
                return False

            # Build forest of trees and calculate metrics
            self.metrics = classifier.fit_and_calculate_metrics(0.25)

            self.setProgress(75)
            if self.isCanceled():
                return False

            if self.do_prediction:
                places_prediction = self.obtain_places(self.prediction_directory)
                self.pre_process_images(places_prediction)
                self.predict(places_prediction, classifier, self.output_file)

            self.setProgress(100)

            self.elapsed_time = time.time() - self.start_time
            print("Finished in {} seconds".format(str(self.elapsed_time)))

            if self.isCanceled():
                return False

            return True

        except Exception as e:
            self.exception = e
            return False

    def finished(self, result):
        """
        This function is automatically called when the task has completed (successfully or not).
        You implement finished() to do whatever follow-up stuff should happen after the task is complete.
        finished is always called from the main thread, so it's safe
        to do GUI operations and raise Python exceptions here.
        result is the return value from self.run.
        """
        if result:
            QgsMessageLog.logMessage(
                'Task "{name}" completed in {time} seconds\n' \
                'Training Directory: {td})'.format(
                  name=self.description(),
                  time=self.elapsed_time,
                  td=self.training_directory),
              MESSAGE_CATEGORY, Qgis.Success)

            self.li.notify_metrics(self.start_time_str, self.classes_training, self.classes_output, self.metrics, self.elapsed_time)
            self.li.notify_task(self.start_time_str)

        else:
            if self.exception is None:
                QgsMessageLog.logMessage(
                    'Task "{name}" not successful but without '\
                    'exception (probably the task was manually '\
                    'canceled by the user)'.format(
                        name=self.description()),
                    MESSAGE_CATEGORY, Qgis.Warning)
            else:
                QgsMessageLog.logMessage(
                    'Task "{name}" Exception: {exception}'.format(
                        name=self.description(),
                        exception=self.exception),
                    MESSAGE_CATEGORY, Qgis.Critical)
                raise self.exception

    def cancel(self):
        QgsMessageLog.logMessage(
            'Task "{name}" was canceled'.format(
                name=self.description()),
            MESSAGE_CATEGORY, Qgis.Info)
        super().cancel()
