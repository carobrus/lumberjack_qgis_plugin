from argparse import ArgumentParser
from osgeo import gdal
from osgeo import gdal_array
from scipy import ndimage
import numpy as np
import time


def generate_empty_img(dataset):
    # Allocates the array using the first band's datatype
    image_datatype = dataset.GetRasterBand(1).DataType
    empty_img = np.zeros((dataset.RasterYSize,
                            dataset.RasterXSize,
                            dataset.RasterCount),
                            dtype=gdal_array.GDALTypeCodeToNumericTypeCode(image_datatype))
    return empty_img


def median_filter(dataset, window_size):
    img_filtered = generate_empty_img(dataset)
    # Loops all the bands of the image and
    for b in range(dataset.RasterCount):
        band = dataset.GetRasterBand(b + 1)
        # Read in the band's data into the third dimension of our array
        img_filtered[:, :, b] = ndimage.filters.median_filter(band.ReadAsArray(),
                                                            size = (window_size, window_size))
    return img_filtered


def gaussian_filter(dataset, sigma):
    img_filtered = generate_empty_img(dataset)
    # Loops all the bands of the image and
    for b in range(dataset.RasterCount):
        band = dataset.GetRasterBand(b + 1)
        # Read in the band's data into the third dimension of our array
        img_filtered[:, :, b] = ndimage.gaussian_filter(band.ReadAsArray(), sigma=sigma)
    return img_filtered


def output_tiff(dataset, img_filtered, file_output):
    memory_driver = gdal.GetDriverByName('GTiff')
    out_raster_ds = memory_driver.Create(file_output, dataset.RasterXSize, dataset.RasterYSize, dataset.RasterCount, gdal.GDT_Float32)
    out_raster_ds.SetProjection(dataset.GetProjectionRef())
    out_raster_ds.SetGeoTransform(dataset.GetGeoTransform())
    for b in range(dataset.RasterCount):
        outband = out_raster_ds.GetRasterBand(b+1)
        outband.WriteArray(img_filtered[:, :, b])
    outband.FlushCache()
    out_raster_ds = None


def generate_filter_file(file_input, file_output_median, file_output_gaussian, window_size=4, sigma=1):
    start_time = time.time()
    print("Performing filters...")
    # Opens the gdal dataset
    dataset = gdal.Open(file_input, gdal.GA_ReadOnly)

    if file_output_median != None:
        median_img = median_filter(dataset, window_size)
        output_tiff(dataset, median_img, file_output_median)

    if file_output_gaussian != None:
        gaussian_img = gaussian_filter(dataset, sigma)
        output_tiff(dataset, gaussian_img, file_output_gaussian)

    elapsed_time = time.time() - start_time
    print("Finished filtering in " + str(elapsed_time) + " seconds")


def check_positive(value):
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError("%s is an invalid positive int value" % value)
    return ivalue


if __name__== "__main__":
    parser = ArgumentParser()
    parser.add_argument("-i", "--input_file", dest="file_input",
                        help="Input tiff file to perform filters", required=True)
    parser.add_argument("-om", "--output_file_median", dest="file_output_median",
                        help="Output tiff file to save the image filtered by median method", required=False)
    parser.add_argument("-og", "--output_file_gaussian", dest="file_output_gaussian",
                        help="Output tiff file to save the image filtered by gaussian method", required=False)
    parser.add_argument("-w", "--window_size", dest="window_size", type=check_positive,
                        help="Size of the window", required=False)
    parser.add_argument("-s", "--sigma", dest="sigma", type=check_positive,
                        help="Standard deviation for Gaussian kernel", required=False)
    args = parser.parse_args()
    generate_filter_file(args.file_input, args.file_output_median, args.file_output_gaussian, args.window_size, sigma)
