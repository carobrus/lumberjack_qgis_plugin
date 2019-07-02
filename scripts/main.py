import os
import subprocess
import time
from osgeo import gdal
from osgeo import ogr
import numpy as np
from classifier import Classifier
import bands_algebra
import filters
import NDVI


def crop_and_merge(training_directory, tiff_extension_filename):
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
            for tiff_file in os.listdir(file.path):
                if (tiff_file[-9:-5] == "band"):
                    band_number += 1

                    print("Cropping Tiff file: {}".format(tiff_file))
                    # Crop image to extension
                    subprocess.call("gdal_translate -projwin {} {} {} {} -ot Int16 -of GTiff \"{}/{}\" \"{}/{}{}{}\"".format(minx, maxy, maxx, miny, file.path, tiff_file, file.path, tiff_file[:-5], str(band_number), "crop.tif"), stdout=open(os.devnull, 'wb'))
                    ds = gdal.Open("{}/{}{}crop.tif".format(file.path, tiff_file[:-5], str(band_number)), gdal.GA_ReadOnly)
                    if (band_number == 1):
                        driver = gdal.GetDriverByName('GTiff')
                        outRaster = driver.Create("{}/{}merged.tif".format(file.path, tiff_file[:-9]), ext_ds.RasterXSize, ext_ds.RasterYSize, 7, gdal.GDT_Int16)
                        outRaster.SetGeoTransform(ext_ds.GetGeoTransform())
                        outRaster.SetProjection(ext_ds.GetProjection())
                    band_cropped = ds.GetRasterBand(1).ReadAsArray()
                    outband = outRaster.GetRasterBand(band_number)
                    outband.WriteArray(band_cropped)
            outband.FlushCache()


def calculate_features(training_directory):
    for file in os.scandir(training_directory):
        if (file.is_dir()):
            print("Directory: {}".format(file.path))
            # For each file whose name it's like *band_____
            for tiff_file in os.listdir(file.path):
                if (tiff_file[-10:] == "merged.tif"):
                    print("Generating features to file: {}".format(tiff_file))
                    # Calculate features
                    abs_path_tiff_file = "{}/{}".format(file.path, tiff_file)
                    bands_algebra.generate_algebra_file(abs_path_tiff_file, "{}/{}{}".format(file.path, tiff_file[:-4], "_alge.tif"))
                    NDVI.generate_ndvi_file(abs_path_tiff_file, "{}/{}{}".format(file.path, tiff_file[:-4], "_ndvi.tif"))
                    filters.generate_filter_file(abs_path_tiff_file, "{}/{}{}".format(file.path, tiff_file[:-4], "_filt.tif"))


def stack_features(training_directory):
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
                    out_raster_ds = memory_driver.Create(new_file_name, dataset.RasterXSize, dataset.RasterYSize, 19, gdal.GDT_Float32)
                    out_raster_ds.SetProjection(dataset.GetProjectionRef())
                    out_raster_ds.SetGeoTransform(dataset.GetGeoTransform())
                    for band_number in range(dataset.RasterCount):
                        band_total += 1
                        band = dataset.GetRasterBand(band_number + 1)
                        outband = out_raster_ds.GetRasterBand(band_total)
                        outband.WriteArray(band.ReadAsArray())

                if (tiff_file[-15:-9] == "merged"):
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
    roi_ds = gdal.Open(rasterized_vector_file, gdal.GA_ReadOnly)
    roi = roi_ds.GetRasterBand(1).ReadAsArray().astype(np.uint8)

    classes = np.unique(roi)
    # Iterate over all class labels in the ROI image, printing out some information
    for c in classes:
        print('Class {c} contains {n} pixels'.format(c=c, n=(roi == c).sum()))

    # Find how many non-zero entries there are
    n_samples = (roi > 0).sum()
    print('There are {n} samples'.format(n=n_samples))


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


def main():
    start_time = time.time()

    tiff_extension_file = "C:/Users/Carolina/Documents/Tesis/GeneralVillegas(4estaciones)/LC08_L1TP_228084_20160706_20170323_01_T1_sr_clipped.tif"
    training_directory = "C:/Users/Carolina/Documents/Tesis/Tiff Files/HighLevel/espa-bruscantinic@gmail.com-0101811141560"

    # crop_and_merge(training_directory, tiff_extension_file)
    # calculate_features(training_directory)
    # stack_features(training_directory)

    vector_file_name = "C:/Users/Carolina/Documents/Tesis/GeneralVillegas(4estaciones)/roi.shp"
    rasterized_vector_file = "C:/Users/Carolina/Documents/Tesis/GeneralVillegas(4estaciones)/roi.tif" #Rasterize

    rasterize_vector_file(vector_file_name, rasterized_vector_file, tiff_extension_file)
    check_classes(rasterized_vector_file)

    classifier = Classifier()
    add_samples(training_directory, classifier, rasterized_vector_file)
    classifier.fit_and_calculate_metrics()


    prediction_result_img = "C:/Users/Carolina/Documents/Tesis/Pruebas/result.tif"
    tiff_extension_file_to_predict = "C:/Users/Carolina/Documents/Tesis/Tiff Files/HighLevel/espa-bruscantinic@gmail.com-0101811141571/LC082250852018072301T1-SC20181114131415/LC08_L1TP_225085_20180723_20180731_01_T1_sr_band1_clipped.tif"
    download_directory = "C:/Users/Carolina/Documents/Tesis/Tiff Files/HighLevel/espa-bruscantinic@gmail.com-0101811141571"
    crop_and_merge(download_directory, tiff_extension_file_to_predict)
    calculate_features(download_directory)
    stack_features(download_directory)
    predict(download_directory, classifier, prediction_result_img)

    elapsed_time = time.time() - start_time
    print("Finished in {} seconds".format(str(elapsed_time)))


if __name__== "__main__":
    main()
