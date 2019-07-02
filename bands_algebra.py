from argparse import ArgumentParser
from osgeo import gdal
import numpy as np
import time


def obtain_features(dataset, file_output):
    rasterCount = dataset.RasterCount

    # Levanta todas las bandas en 'data'
    data=[]
    for band in range(rasterCount):
        band += 1
        srcband = dataset.GetRasterBand(band)
        if srcband is None:
            continue
        data.append(srcband.ReadAsArray().astype(np.float))

    srcband.FlushCache()
    srcband = None

    # Calcula media y std de cada pixel
    mean = np.mean(data, axis=0)
    std = np.std(data, axis=0)

    # Obtiene la dimension de data, que es la dimension de la imagen
    # y le da un formato nuevo a la matriz
    dim = np.shape(data)
    data = np.reshape(data,(rasterCount,dim[1]*dim[2]))
    print('Image dimension:', dim)

    # Calcula la pendiente y ordenada al origen de la fitted line
    x = np.arange(1,rasterCount+1)
    A = np.vstack([x, np.ones(len(x))]).T
    # We can rewrite the line equation as y = Ap, where A = [[x 1]] and p = [[m], [c]].
    # Now use lstsq to solve for p:
    m, c = np.linalg.lstsq(A,data, rcond=None)[0]
    m = np.reshape(m,(dim[1],dim[2]))
    c = np.reshape(c,(dim[1],dim[2]))
    data = None

    # Escribe las 4 matrices (media, std, pendiente y ordenada el origen
    # de ajuste lineal) en una imagen nueva
    driver = gdal.GetDriverByName('GTiff')
    outRaster = driver.Create(file_output, dim[2], dim[1], 4, gdal.GDT_Float32)
    outRaster.SetGeoTransform(dataset.GetGeoTransform())#Edito la georeferencia
    outRaster.SetProjection(dataset.GetProjection())
    #Por cada matriz escribo en una banda
    outband = outRaster.GetRasterBand(1)
    outband.WriteArray(mean) #escribo la matriz en el raster
    outband = outRaster.GetRasterBand(2)
    outband.WriteArray(std)
    outband = outRaster.GetRasterBand(3)
    outband.WriteArray(m)
    outband = outRaster.GetRasterBand(4)
    outband.WriteArray(c)
    outband.FlushCache()
    outRaster = None
    outband = None


def generate_algebra_file(file_input, file_output):
    start_time = time.time()
    print("Performing mean, std and fitted line slope and intersection...")
    # Opens the gdal dataset
    dataset = gdal.Open(file_input, gdal.GA_ReadOnly)

    obtain_features(dataset, file_output)

    elapsed_time = time.time() - start_time
    print("Finished generating mean, std and fitted line features in "
          + str(elapsed_time) + " seconds")


if __name__== "__main__":
    parser = ArgumentParser()
    parser.add_argument("-i", "--input_file", dest="file_input",
                        help="Input tiff file to perform filters", required=True)
    parser.add_argument("-o", "--output_file", dest="file_output",
                        help="Output tiff file to save the image filtered", required=True)
    args = parser.parse_args()
    generate_algebra_file(args.file_input, args.file_output)
