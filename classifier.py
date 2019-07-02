from argparse import ArgumentParser
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix
from osgeo import gdal
from osgeo import gdal_array
from osgeo import ogr
import numpy as np


class Classifier:
    __X = []
    __y = []
    __outfile_name = None
    __rf = None


    def add_samples(self, input_tiff_file, rasterized_file):
        dataset = gdal.Open(input_tiff_file, gdal.GA_ReadOnly)
        new_features_array = np.zeros((dataset.RasterYSize, dataset.RasterXSize, dataset.RasterCount), dtype=np.float32)
        print("Shape array features: {}".format(new_features_array.shape))
        for band_number in range(dataset.RasterCount):
            band = dataset.GetRasterBand(band_number + 1)
            # Read in the band's data into the third dimension of our array
            new_features_array[:, :, band_number] = band.ReadAsArray()

        roi_ds = gdal.Open(rasterized_file, gdal.GA_ReadOnly)
        roi = roi_ds.GetRasterBand(1).ReadAsArray().astype(np.uint8)
        X = new_features_array[roi > 0, :]
        y = roi[roi > 0]
        if (len(self.__y) == 0):
            self.__X = X
            self.__y = y
        else:
            self.__X = np.append(self.__X, X, axis=0)
            self.__y = np.append(self.__y, y)
        print("X size: {}".format(self.__X.shape))
        print("y size: {}".format(self.__y.shape))


    def fit_and_calculate_metrics(self):
        X_train, X_test, y_train, y_test = train_test_split(self.__X, self.__y)
        print("X_train matrix is sized: {size}".format(size=X_train.shape))
        print("y_train array is sized: {size}".format(size=y_train.shape))
        print("X_test matrix is sized: {size}".format(size=X_test.shape))
        print("y_test array is sized: {size}".format(size=y_test.shape))

        # Initializes model with 500 trees
        # self.__rf = RandomForestClassifier(n_estimators=500, oob_score=True, n_jobs=-1)
        self.__rf = RandomForestClassifier(n_estimators=500, oob_score=True)

        print("Fitting model to training data...")
        # Build a forest of trees from the training set (X, y).
        self.__rf = self.__rf.fit(X_train, y_train)

        #  Score of the training dataset obtained using an out-of-bag estimate.
        print("The OOB prediction of accuracy is: {}%".format(self.__rf.oob_score_ * 100))

        for index, imp in enumerate(self.__rf.feature_importances_):
            print('Feature {:>4} importance: {}'.format(index+1, imp))

        c_matrix = confusion_matrix(y_test, self.__rf.predict(X_test), labels=[1,2])

        print("")
        print("Confusion Matrix")
        print(c_matrix)

        return self.__rf.feature_importances_


    def predict_an_image(self, input_image, output_image):
        dataset = gdal.Open(input_image, gdal.GA_ReadOnly)
        feats_img_to_predict = np.zeros((dataset.RasterYSize, dataset.RasterXSize, dataset.RasterCount), dtype=np.float32)
        for band_number in range(dataset.RasterCount):
            band = dataset.GetRasterBand(band_number + 1)
            # Read in the band's data into the third dimension of our array
            feats_img_to_predict[:, :, band_number] = band.ReadAsArray()


        new_shape = (feats_img_to_predict.shape[0] * feats_img_to_predict.shape[1], feats_img_to_predict.shape[2])
        img_as_array = feats_img_to_predict[:, :, :dataset.RasterCount].reshape(new_shape)
        print('Reshaped from {old_shape} to {new_shape}'.format(old_shape=feats_img_to_predict.shape, new_shape=img_as_array.shape))

        # Predicts for each pixel
        print("Predicting rest of the image...")
        class_prediction = self.__rf.predict(img_as_array)

        # Reshape classification map
        class_prediction = class_prediction.reshape(feats_img_to_predict[:, :, 0].shape)

        # Create the result tiff
        print("Creating output image...")
        memory_driver = gdal.GetDriverByName('GTiff')
        out_raster_ds = memory_driver.Create(output_image, dataset.RasterXSize, dataset.RasterYSize, 1, gdal.GDT_Byte)
        out_raster_ds.SetProjection(dataset.GetProjectionRef())
        out_raster_ds.SetGeoTransform(dataset.GetGeoTransform())
        outband = out_raster_ds.GetRasterBand(1)
        outband.WriteArray(class_prediction)
        outband.FlushCache()
        out_raster_ds = None
