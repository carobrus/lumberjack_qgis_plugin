from argparse import ArgumentParser
from osgeo import gdal
from osgeo import gdal_array
import numpy as np
import time


def calculate_ndvi(dataset):
    # Allocate the array using the first band's datatype
    image_datatype = dataset.GetRasterBand(1).DataType
    image = np.zeros((dataset.RasterYSize, dataset.RasterXSize, 2),
                     dtype=gdal_array.GDALTypeCodeToNumericTypeCode(image_datatype))

    # Read Red band
    b_red = 0
    band = dataset.GetRasterBand(4)
    image[:, :, b_red] = band.ReadAsArray()
    # Read NIR band
    b_nir = 1
    band = dataset.GetRasterBand(5)
    image[:, :, b_nir] = band.ReadAsArray()

    # print('Red band mean: {r}'.format(r=image[:, :, b_red].mean()))
    # print('NIR band mean: {nir}'.format(nir=image[:, :, b_nir].mean()))

    ndvi = (image[:, :, b_nir] - image[:, :, b_red]) / (image[:, :, b_red] + image[:, :, b_nir])
    return ndvi


def output_tiff(dataset, ndvi, file_output):
    memory_driver = gdal.GetDriverByName('GTiff')
    out_raster_ds = memory_driver.Create(file_output, dataset.RasterXSize, dataset.RasterYSize, 1, gdal.GDT_Float32)
    out_raster_ds.SetProjection(dataset.GetProjectionRef())
    out_raster_ds.SetGeoTransform(dataset.GetGeoTransform())
    outband = out_raster_ds.GetRasterBand(1)
    outband.WriteArray(ndvi)
    outband.FlushCache()
    out_raster_ds = None


def generate_ndvi_file(file_input, file_output):
    start_time = time.time()
    print("Calculating NDVI...")
    # Opens the gdal dataset
    dataset = gdal.Open(file_input, gdal.GA_ReadOnly)
    img = calculate_ndvi(dataset)
    output_tiff(dataset, img, file_output)
    elapsed_time = time.time() - start_time
    print("Finished calculating NDVI in " + str(elapsed_time) + " seconds")


if __name__== "__main__":
    parser = ArgumentParser()
    parser.add_argument("-i", "--input_file", dest="file_input",
                        help="Input tiff file to perform filters", required=True)
    parser.add_argument("-o", "--output_file", dest="file_output",
                        help="Output tiff file to save the image filtered", required=True)
    args = parser.parse_args()
    generate_ndvi_file(args.file_input, args.file_output)
