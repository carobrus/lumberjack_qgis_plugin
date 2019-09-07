import os
import subprocess
import time
import datetime
from osgeo import gdal
from osgeo import ogr
import numpy as np
from .classifier import Classifier
from . import bands_algebra
from . import filters
from . import ndvi
from . import threshold
import math


class Main():

    def crop_and_merge(self, training_directory, tiff_extension_filename):
        """
        Crops all images in the directory according to a given file. Adds "crop" to the filename just before the extension.
        It merges all the cropped images and creates a new file with the "merged" suffix.
        """
        ext_ds = gdal.Open(tiff_extension_filename, gdal.GA_ReadOnly)
        # Get Extension
        geoTransform = ext_ds.GetGeoTransform()
        minx = geoTransform[0]
        maxy = geoTransform[3]
        maxx = minx + geoTransform[1] * ext_ds.RasterXSize
        miny = maxy + geoTransform[5] * ext_ds.RasterYSize

        # For each folder in training_directory
        for file in os.scandir(training_directory):
            if (file.is_dir()):
                print("Directory: {}".format(file.path))
                band_number = 0
                outRaster = None
                outband = None
                # For each file whose name it's like *band_____
                file_name = ""
                for tiff_file in os.listdir(file.path):
                    if (tiff_file[-9:-5] == "band"):
                        band_number += 1
                        print("Cropping Tiff file: {}".format(tiff_file))
                        # Crop image to extension
                        subprocess.call("gdal_translate -projwin {} {} {} {} -ot Int16 -of GTiff \"{}/{}\" \"{}/{}{}{}\"".format(minx, maxy, maxx, miny, file.path, tiff_file, file.path, tiff_file[:-5], str(band_number), "crop.tif"), stdout=open(os.devnull, 'wb'), shell=True)
                        ds = gdal.Open("{}/{}{}crop.tif".format(file.path, tiff_file[:-5], str(band_number)), gdal.GA_ReadOnly)
                        if (band_number == 1):
                            driver = gdal.GetDriverByName('GTiff')
                            file_name = "{}/{}merged.tif".format(file.path, tiff_file[:-9])
                            # if os.path.exists(file_name):
                                # os.remove(file_name)
                            outRaster = driver.Create(file_name, ext_ds.RasterXSize, ext_ds.RasterYSize, 7, gdal.GDT_Int16)
                            #print ("Creating file: " + file_name)
                            outRaster.SetGeoTransform(ext_ds.GetGeoTransform())
                            outRaster.SetProjection(ext_ds.GetProjection())
                        band_cropped = ds.GetRasterBand(1).ReadAsArray()
                        outband = outRaster.GetRasterBand(band_number)
                        outband.WriteArray(band_cropped)
                print ("File created: " + file_name)
                outband.FlushCache()


    def calculate_features(self, training_directory, do_algebra, do_filters, do_ndvi):
        for file in os.scandir(training_directory):
            if (file.is_dir()):
                print("Directory: {}".format(file.path))
                # For each file whose name it's like *band_____
                for tiff_file in os.listdir(file.path):
                    if (tiff_file[-10:] == "merged.tif"):
                        print("Generating features to file: {}".format(tiff_file))
                        # Calculate features
                        abs_path_tiff_file = "{}/{}".format(file.path, tiff_file)
                        if do_algebra:
                            bands_algebra.generate_algebra_file(abs_path_tiff_file, "{}/{}{}".format(file.path, tiff_file[:-4], "_alge.tif"))
                        if do_ndvi:
                            ndvi.generate_ndvi_file(abs_path_tiff_file, "{}/{}{}".format(file.path, tiff_file[:-4], "_ndvi.tif"))
                        if do_filters:
                            filters.generate_filter_file(abs_path_tiff_file, "{}/{}{}".format(file.path, tiff_file[:-4], "_filt.tif"), "{}/{}{}".format(file.path, tiff_file[:-4], "_gaus.tif"))


    def stack_features(self, training_directory, do_algebra, do_filters, do_ndvi, do_textures, do_dem, dem_file):
        rasterCount = 7
        if do_algebra:
            rasterCount += 4
        if do_filters:
            rasterCount += 14
        if do_ndvi:
            rasterCount += 1
        if do_textures:
            rasterCount += 35
        if do_dem:
            rasterCount += 7

        for file in os.scandir(training_directory):
            if (file.is_dir()):
                print("Directory: {}".format(file.path))
                outband = None
                out_raster_ds = None
                number_of_day_normalized = None
                number_of_day_transform = None
                # For each file whose name it's like *band_____
                band_total = 0
                for tiff_file in os.listdir(file.path):
                    if (tiff_file[-10:] == "merged.tif"):
                        abs_path_tiff_file = "{}/{}".format(file.path, tiff_file)
                        new_file_name = "{}/{}{}".format(file.path, tiff_file[:-10], "stack.tif")
                        print("Creating file: {}{}".format(tiff_file[:-10], "stack.tif"))
                        dataset = gdal.Open(abs_path_tiff_file, gdal.GA_ReadOnly)
                        memory_driver = gdal.GetDriverByName('GTiff')
                        if os.path.exists(new_file_name):
                            os.remove(new_file_name)
                        out_raster_ds = memory_driver.Create(new_file_name, dataset.RasterXSize, dataset.RasterYSize, rasterCount, gdal.GDT_Float32)
                        out_raster_ds.SetProjection(dataset.GetProjectionRef())
                        out_raster_ds.SetGeoTransform(dataset.GetGeoTransform())
                        for band_number in range(dataset.RasterCount):
                            band_total += 1
                            band = dataset.GetRasterBand(band_number + 1)
                            outband = out_raster_ds.GetRasterBand(band_total)
                            outband.WriteArray(band.ReadAsArray())

                    if (tiff_file[-8:] == "alge.tif" and do_algebra) or (tiff_file[-8:] == "ndvi.tif" and do_ndvi) or (tiff_file[-8:] == "filt.tif" and do_filters) or (tiff_file[-8:] == "gaus.tif" and do_filters) or (tiff_file[-8:] == "text.tif" and do_textures):
                        abs_path_tiff_file = "{}/{}".format(file.path, tiff_file)
                        dataset = gdal.Open(abs_path_tiff_file, gdal.GA_ReadOnly)
                        for band_number in range(dataset.RasterCount):
                            band_total += 1
                            band = dataset.GetRasterBand(band_number + 1)
                            outband = out_raster_ds.GetRasterBand(band_total)
                            outband.WriteArray(band.ReadAsArray())

                    if (tiff_file[-8:] == "_MTL.txt" and do_dem):
                        date = get_date_from_metadata("{}/{}".format(file.path, tiff_file))
                        number_of_day = transform_day(date)
                        number_of_day_normalized = number_of_day / 366
                        number_of_day_transform = math.sin(number_of_day_normalized * math.pi)

                if do_dem:
                    dataset = gdal.Open(dem_file, gdal.GA_ReadOnly)
                    for band_number in range(dataset.RasterCount):
                        band_total += 1
                        band = dataset.GetRasterBand(band_number + 1)
                        outband = out_raster_ds.GetRasterBand(band_total)
                        outband.WriteArray(band.ReadAsArray())
                    # Add the number of day in the year for every pixel
                    band_total += 1
                    band = np.full((dataset.RasterYSize, dataset.RasterXSize), number_of_day_normalized)
                    outband = out_raster_ds.GetRasterBand(band_total)
                    outband.WriteArray(band)
                    band_total += 1
                    band = np.full((dataset.RasterYSize, dataset.RasterXSize), number_of_day_transform)
                    outband = out_raster_ds.GetRasterBand(band_total)
                    outband.WriteArray(band)

                outband.FlushCache()
                out_raster_ds = None


    def transform_day(self, date):
        year, month, day = date.split("-")
        year = int(year)
        month = int(month)
        day = int(day)
        number_of_day = (datetime.date(year, month, day) - datetime.date(year,1,1)).days + 1
        return number_of_day


    def get_date_from_metadata(self, file):
        f = open(file, 'r')
        for line in f.readlines():
            if "DATE_ACQUIRED =" in line:
                l = line.split("=")
                return l[1]


    def rasterize_vector_file(self, vector_file_name, rasterized_vector_file, tiff_file):
        # Rasterize
        tiff_dataset = gdal.Open(tiff_file, gdal.GA_ReadOnly)
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

        vector_dataset = ogr.Open(vector_file_name)
        layer = vector_dataset.GetLayerByIndex(0)
        # Rasterize the shapefile layer to our new dataset
        status = gdal.RasterizeLayer(out_raster_ds, [1], layer, None, None, [0], ['ALL_TOUCHED=TRUE', 'ATTRIBUTE=id'])

        # Close dataset
        out_raster_ds = None

        if status != 0:
            print("Error creating rasterized tiff")
        else:
            print("Rasterize tiff created")


    def add_samples(self, training_directory, classifier, rasterized_vector_file):
        for file in os.scandir(training_directory):
            if (file.is_dir()):
                print("Directory: {}".format(file.path))
                # For each file whose name it's like *band_____
                for tiff_file in os.listdir(file.path):
                    if (tiff_file[-9:] == "stack.tif"):
                        print("File: {}".format(tiff_file))
                        file_name = "{}/{}".format(file.path, tiff_file)
                        classifier.add_samples(file_name, rasterized_vector_file)


    def add_test_samples(self, training_directory, classifier, rasterized_vector_file):
        for file in os.scandir(training_directory):
            if (file.is_dir()):
                print("Directory: {}".format(file.path))
                # For each file whose name it's like *band_____
                for tiff_file in os.listdir(file.path):
                    if (tiff_file[-9:] == "stack.tif"):
                        print("File: {}".format(tiff_file))
                        file_name = "{}/{}".format(file.path, tiff_file)
                        classifier.add_test_samples(file_name, rasterized_vector_file)


    def check_classes(self, rasterized_vector_file):
        output = []
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


    def predict(self, directory, classifier, prediction_result_img):
        for file in os.scandir(directory):
            if (file.is_dir()):
                print("Directory: {}".format(file.path))
                # For each file whose name it's like *band_____
                for tiff_file in os.listdir(file.path):
                    if (tiff_file[-9:] == "stack.tif"):
                        print("File: {}".format(tiff_file))
                        file_name = "{}/{}".format(file.path, tiff_file)
                        classifier.predict_an_image(file_name, prediction_result_img)


    def __init__(self, training_directory, tiff_extension_file, vector_file_name,
                do_algebra, do_filters, do_ndvi, do_textures, do_dem,
                dem_training,
                do_testing, testing_directory, extension_testing,
                vector_testing_roi, dem_testing,
                do_prediction, prediction_directory, extension_prediction,
                dem_prediction, output_file):
        self.training_directory = training_directory
        self.tiff_extension_file = tiff_extension_file
        self.vector_file_name = vector_file_name
        self.do_algebra = do_algebra
        self.do_filters = do_filters
        self.do_ndvi = do_ndvi
        self.do_textures = do_textures
        self.do_dem = do_dem
        self.dem_training = dem_training
        self.do_testing = do_testing
        self.testing_directory = testing_directory
        self.extension_testing = extension_testing
        self.vector_testing_roi = vector_testing_roi
        self.dem_testing = dem_testing
        self.do_prediction = do_prediction
        self.prediction_directory = prediction_directory
        self.extension_prediction = extension_prediction
        self.dem_prediction = dem_prediction
        self.output_file = output_file
        self.exception = None


    def execute(self):
        start_time_str = str(datetime.datetime.now())
        print("============================= " + start_time_str + " =============================")
        start_time = time.time()

        # Prepares training
        # Files to be cropped according the tiff_extension_file (all layers to be cropped and merged)
        self.crop_and_merge(self.training_directory, self.tiff_extension_file)
        self.calculate_features(self.training_directory, self.do_algebra, self.do_filters, self.do_ndvi)
        self.stack_features(self.training_directory, self.do_algebra, self.do_filters, self.do_ndvi, self.do_textures, self.do_dem, self.dem_training)

        # Creates ROI for training
        rasterized_vector_file = self.vector_file_name[:-4] + ".tif" #Rasterize
        print("Creating ROI: " + rasterized_vector_file)
        self.rasterize_vector_file(self.vector_file_name, rasterized_vector_file, self.tiff_extension_file)
        classes_training = self.check_classes(rasterized_vector_file)

        # Create classifier and add samples to train
        classifier = Classifier()
        self.add_samples(self.training_directory, classifier, rasterized_vector_file)

        classes_output = None
        if (self.do_testing):
            # Calculate features for testing files
            self.crop_and_merge(self.testing_directory, self.extension_testing)
            self.calculate_features(self.testing_directory, self.do_algebra, self.do_filters, self.do_ndvi)
            self.stack_features(self.testing_directory, self.do_algebra, self.do_filters, self.do_ndvi, self.do_textures, self.do_dem, self.dem_testing)

            # Creates ROI for testing
            rasterized_vector_testing = self.vector_testing_roi[:-4] + ".tif" #Rasterize
            print("Creating ROI: " + rasterized_vector_testing)
            self.rasterize_vector_file(self.vector_testing_roi, rasterized_vector_testing, self.extension_testing)
            classes_output = check_classes(rasterized_vector_testing)

            self.add_test_samples(self.testing_directory, classifier, rasterized_vector_testing)

        # Build forest of trees and calculate metrics
        metrics = classifier.fit_and_calculate_metrics(0.25)

        if self.do_prediction:
            # Calculate features for image to predict
            self.crop_and_merge(self.prediction_directory, self.extension_prediction)
            self.calculate_features(self.prediction_directory, self.do_algebra, self.do_filters, self.do_ndvi)
            self.stack_features(self.prediction_directory, self.do_algebra, self.do_filters, self.do_ndvi, self.do_textures, self.do_dem, self.dem_prediction)

            self.predict(self.prediction_directory, classifier, self.output_file)

        elapsed_time = time.time() - start_time
        print("Finished in {} seconds".format(str(elapsed_time)))

        return [metrics, classes_training, classes_output, start_time, "Finished in {} seconds".format(str(elapsed_time))]


    def calculate_threshold(self):
        return threshold.calculate_threshold()


# if __name__== "__main__":
#     execute()
