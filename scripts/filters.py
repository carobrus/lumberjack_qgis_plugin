from argparse import ArgumentParser
from osgeo import gdal
from osgeo import gdal_array
from scipy import ndimage
import numpy as np
import time

WINDOW_SIZE = 4


def generate_empty_img(dataset):
    # Allocates the array using the first band's datatype
    image_datatype = dataset.GetRasterBand(1).DataType
    empty_img = np.zeros((dataset.RasterYSize,
                            dataset.RasterXSize,
                            dataset.RasterCount),
                            dtype=gdal_array.GDALTypeCodeToNumericTypeCode(image_datatype))
    return empty_img


def median_filter(dataset):
    img_filtered = generate_empty_img(dataset)
    # Loops all the bands of the image and
    for b in range(dataset.RasterCount):
        band = dataset.GetRasterBand(b + 1)
        # Read in the band's data into the third dimension of our array
        img_filtered[:, :, b] = ndimage.filters.median_filter(band.ReadAsArray(),
                                                            size = (WINDOW_SIZE, WINDOW_SIZE))
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


def import_to_qgis(file_output, name_output):
    iface.addRasterLayer(file_output, name_output)


def generate_filter_file(file_input, file_output):
    start_time = time.time()
    print("Performing filters...")
    # Opens the gdal dataset
    dataset = gdal.Open(file_input, gdal.GA_ReadOnly)
    median_img = median_filter(dataset)
    output_tiff(dataset, median_img, file_output)
    elapsed_time = time.time() - start_time
    print("Finished filtering in " + str(elapsed_time) + " seconds")


if __name__== "__main__":
    parser = ArgumentParser()
    parser.add_argument("-i", "--input_file", dest="file_input",
                        help="Input tiff file to perform filters", required=True)
    parser.add_argument("-o", "--output_file", dest="file_output",
                        help="Output tiff file to save the image filtered", required=True)
    args = parser.parse_args()
    generate_filter_file(args.file_input, args.file_output)

# TODO: Add argument for WINDOW_SIZE
# TODO: Make gaussian filter with ndimage.gaussian_filter(...) method
