from osgeo import gdal
import numpy as np


def calculate_threshold():
    mask_layer_file = "C:/Users/Carolina/Desktop/GralVillegasMarzo/result.tif"
    features_file = "C:/Users/Carolina/Documents/Tesis/Tiff Files/HighLevel/espa-bruscantinic@gmail.com-0101811141571/Enero/LC082250852018012801T1-SC20181114130831/LC08_L1TP_225085_20180128_20180207_01_T1_sr_stack.tif"

    mask = gdal.Open(mask_layer_file, gdal.GA_ReadOnly)
    mask_array = mask.GetRasterBand(1).ReadAsArray().astype(np.uint8)

    ft = gdal.Open(features_file, gdal.GA_ReadOnly)
    band_arrays = np.zeros((ft.RasterYSize, ft.RasterXSize, ft.RasterCount), dtype=np.float32)
    for b in range(ft.RasterCount):
        band = ft.GetRasterBand(b + 1)
        band_arrays[:, :, b] = band.ReadAsArray()

    band_filtered = band_arrays[mask_array < 2, :]

    # for b in range(5):
    #     print(str(np.min(band_filtered[:,b])),str(np.max(band_filtered[:,b])),str(np.mean(band_filtered[:,b])),str(np.median(band_filtered[:,b])))
    # print(np.min(band_filtered, axis=0))
    # print(np.max(band_filtered, axis=0))
    # print(np.mean(band_filtered, axis=0))
    # print(np.median(band_filtered, axis=0))

    return band_filtered
