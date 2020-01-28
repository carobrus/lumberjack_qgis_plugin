from .preprocess_task import *


class ClassificationTask(PreProcessTask):
    def __init__(self, description, task):
        super().__init__(description, task)


    def filter_samples(self, places):
        for place in places:
            roi_dataset = gdal.Open(place.vector_file_path[:-4]+".tif", gdal.GA_ReadOnly)
            roi = roi_dataset.GetRasterBand(1).ReadAsArray().astype(np.uint8)
            y = roi[roi > 0]

            for image in place.images:
                file_name_stack = os.path.join(image.path, "{}{}".format(image.base_name, Lumberjack.STACK_SUFFIX))

                dataset = gdal.Open(file_name_stack, gdal.GA_ReadOnly)

                features_array = np.zeros(
                    (roi_dataset.RasterYSize, roi_dataset.RasterXSize, dataset.RasterCount),
                    dtype=np.float32)
                print("Shape array features: {}".format(features_array.shape))

                for band_number in range(dataset.RasterCount):
                    band = dataset.GetRasterBand(band_number + 1)
                    features_array[:, :, band_number] = band.ReadAsArray()

                # Create X and y that's going have all the features and
                # labels to be easily used later with the classifier
                X = features_array[roi > 0, :]

                print("X size: {}".format(X.shape))
                print("y size: {}".format(y.shape))

                self.add_samples(X, y)


    def rasterize_vector_files(self, places):
        for place in places:
            rasterized_vector_file = place.vector_file_path[:-4] + ".tif"
            print("Creating ROI: " + rasterized_vector_file)

            # Create a new file changing the extension of the shapefile for a
            # GeoTIFF extension, with one band, and the size of the extension
            # file. Byte data type is more than enough for the classes
            tiff_dataset = gdal.Open(place.extension_file_path, gdal.GA_ReadOnly)
            if os.path.exists(rasterized_vector_file):
                os.remove(rasterized_vector_file)
            out_raster_ds = gdal.GetDriverByName('GTiff').Create(
                rasterized_vector_file, tiff_dataset.RasterXSize,
                tiff_dataset.RasterYSize, 1, gdal.GDT_Byte)

            # Set the ROI image's projection and extent to the ones
            # taken from the input extent file
            out_raster_ds.SetProjection(tiff_dataset.GetProjectionRef())
            out_raster_ds.SetGeoTransform(tiff_dataset.GetGeoTransform())
            tiff_dataset = None

            # Fill output band with the 0 blank, no class label
            b = out_raster_ds.GetRasterBand(1)
            b.Fill(0)

            # Open the Shapefile
            vector_dataset = ogr.Open(place.vector_file_path)
            layer = vector_dataset.GetLayerByIndex(0)
            # Rasterize the shapefile layer to the new dataset
            status = gdal.RasterizeLayer(
                out_raster_ds, [1], layer, None, None, [0], ['ALL_TOUCHED=TRUE', 'ATTRIBUTE=id'])

            # Close dataset
            out_raster_ds = None
            if status != 0:
                print("Error creating rasterized tiff")


    def check_classes(self, places):
        self.classes = []
        self.total_samples = 0
        for place in places:
            rasterized_vector_file = place.vector_file_path[:-4] + ".tif"
            roi_ds = gdal.Open(rasterized_vector_file, gdal.GA_ReadOnly)
            roi = roi_ds.GetRasterBand(1).ReadAsArray().astype(np.uint8)

            classes = np.unique(roi)
            # Iterate over all class labels in the ROI image
            for c in classes:
                self.classes.append('Class {c} contains {n} pixels'.format(c=c, n=(roi == c).sum()))

            # Find how many non-zero entries there are
            n_samples = (roi > 0).sum()
            self.total_samples = (self.total_samples + n_samples * len(place.images))
            self.classes.append('There are {n} samples'.format(n=n_samples))
