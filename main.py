import os
import subprocess
import time
from osgeo import gdal
from osgeo import ogr
import numpy as np
from .classifier import Classifier
from . import bands_algebra
from . import filters
from . import ndvi


def crop_and_merge(training_directory, tiff_extension_filename):
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
                    subprocess.call("gdal_translate -projwin {} {} {} {} -ot Int16 -of GTiff \"{}/{}\" \"{}/{}{}{}\"".format(minx, maxy, maxx, miny, file.path, tiff_file, file.path, tiff_file[:-5], str(band_number), "crop.tif"), stdout=open(os.devnull, 'wb'))
                    ds = gdal.Open("{}/{}{}crop.tif".format(file.path, tiff_file[:-5], str(band_number)), gdal.GA_ReadOnly)
                    if (band_number == 1):
                        driver = gdal.GetDriverByName('GTiff')
                        file_name = "{}/{}merged.tif".format(file.path, tiff_file[:-9])
                        if os.path.exists(file_name):
                            os.remove(file_name)
                        outRaster = driver.Create(file_name, ext_ds.RasterXSize, ext_ds.RasterYSize, 7, gdal.GDT_Int16)
                        #print ("Creating file: " + file_name)
                        outRaster.SetGeoTransform(ext_ds.GetGeoTransform())
                        outRaster.SetProjection(ext_ds.GetProjection())
                    band_cropped = ds.GetRasterBand(1).ReadAsArray()
                    outband = outRaster.GetRasterBand(band_number)
                    outband.WriteArray(band_cropped)
            print ("File created: " + file_name)
            outband.FlushCache()


def calculate_features(training_directory, do_algebra, do_filters, do_ndvi):
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
                        filters.generate_filter_file(abs_path_tiff_file, "{}/{}{}".format(file.path, tiff_file[:-4], "_filt.tif"))


def stack_features(training_directory, do_algebra, do_filters, do_ndvi, do_textures):
    rasterCount = 7
    if do_algebra:
        rasterCount += 4
    if do_filters:
        rasterCount += 7
    if do_ndvi:
        rasterCount += 1
    if do_textures:
        rasterCount += 35

    for file in os.scandir(training_directory):
        if (file.is_dir()):
            print("Directory: {}".format(file.path))
            outband = None
            out_raster_ds = None
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

                if (tiff_file[-8:] == "alge.tif" and do_algebra) or (tiff_file[-8:] == "ndvi.tif" and do_ndvi) or (tiff_file[-8:] == "filt.tif" and do_filters) or (tiff_file[-8:] == "text.tif" and do_textures):
                    abs_path_tiff_file = "{}/{}".format(file.path, tiff_file)
                    dataset = gdal.Open(abs_path_tiff_file, gdal.GA_ReadOnly)
                    for band_number in range(dataset.RasterCount):
                        band_total += 1
                        band = dataset.GetRasterBand(band_number + 1)
                        outband = out_raster_ds.GetRasterBand(band_total)
                        outband.WriteArray(band.ReadAsArray())

            outband.FlushCache()
            out_raster_ds = None


def rasterize_vector_file(vector_file_name, rasterized_vector_file, tiff_file):
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


def add_samples(training_directory, classifier, rasterized_vector_file):
    for file in os.scandir(training_directory):
        if (file.is_dir()):
            print("Directory: {}".format(file.path))
            # For each file whose name it's like *band_____
            for tiff_file in os.listdir(file.path):
                if (tiff_file[-9:] == "stack.tif"):
                    print("File: {}".format(tiff_file))
                    file_name = "{}/{}".format(file.path, tiff_file)
                    classifier.add_samples(file_name, rasterized_vector_file)


def check_classes(rasterized_vector_file):
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


def predict(directory, classifier, prediction_result_img):
    for file in os.scandir(directory):
        if (file.is_dir()):
            print("Directory: {}".format(file.path))
            # For each file whose name it's like *band_____
            for tiff_file in os.listdir(file.path):
                if (tiff_file[-9:] == "stack.tif"):
                    print("File: {}".format(tiff_file))
                    file_name = "{}/{}".format(file.path, tiff_file)
                    classifier.predict_an_image(file_name, prediction_result_img)


def execute(training_directory, tiff_extension_file, vector_file_name,
            do_algebra, do_filters, do_ndvi, do_textures, do_prediction,
            prediction_directory, tiff_ext_file_prediction,
            output_file):

    start_time = time.time()
    result = []

    # Files to be cropped according the tiff_extension_file (all layers to be cropped and merged)
    crop_and_merge(training_directory, tiff_extension_file)

    calculate_features(training_directory, do_algebra, do_filters, do_ndvi)

    stack_features(training_directory, do_algebra, do_filters, do_ndvi, do_textures)


    rasterized_vector_file = vector_file_name[:-4] + ".tif" #Rasterize

    rasterize_vector_file(vector_file_name, rasterized_vector_file, tiff_extension_file)
    classes_output = check_classes(rasterized_vector_file)

    classifier = Classifier()
    add_samples(training_directory, classifier, rasterized_vector_file)
    output_classification = classifier.fit_and_calculate_metrics()

    if do_prediction:
        crop_and_merge(prediction_directory, tiff_ext_file_prediction)
        calculate_features(prediction_directory, do_algebra, do_filters, do_ndvi)
        stack_features(prediction_directory, do_algebra, do_filters, do_ndvi, do_textures)
        predict(prediction_directory, classifier, output_file)

    elapsed_time = time.time() - start_time
    print("Finished in {} seconds".format(str(elapsed_time)))

    return [output_classification, classes_output, "Finished in {} seconds".format(str(elapsed_time))]

if __name__== "__main__":
    execute()
