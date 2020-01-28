from argparse import ArgumentParser
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.metrics import confusion_matrix
from sklearn.metrics import precision_score
from sklearn.metrics import recall_score
from sklearn.metrics import f1_score
from osgeo import gdal
from osgeo import gdal_array
from osgeo import ogr
import numpy as np
import pickle


class Classifier:
    def __init__(self):
        self.__X_train = None
        self.__y_train = None
        self.__X_test = None
        self.__y_test = None
        self.__rf = None
        self.feature_names = []


    def add_samples(self, X, y, X_data, y_labels):
        if (y_labels is None):
            X_data = X
            y_labels = y
        else:
            X_data = np.append(X_data, X, axis=0)
            y_labels = np.append(y_labels, y)
        return X_data, y_labels


    def add_testing_samples(self,  X, y):
        self.__X_test, self.__y_test = self.add_samples(X, y, self.__X_test, self.__y_test)


    def add_training_samples(self, X, y):
        self.__X_train, self.__y_train = self.add_samples(X, y, self.__X_train, self.__y_train)


    def get_test_size(self):
        return self.__y_test.shape[0]


    def fit(self, test_size):
        if (test_size != 0):
            self.__X_train, self.__X_test, self.__y_train, self.__y_test = (
                train_test_split(
                    self.__X_train, self.__y_train, test_size=test_size))

        # Initializes model with n_estimators trees
        # self.__rf = RandomForestClassifier(n_estimators=500, oob_score=True, n_jobs=-1)
        self.__rf = RandomForestClassifier(n_estimators=100, bootstrap=False)

        print("Fitting model to training data...")
        # Build a forest of trees from the training set (X, y).
        self.__rf = self.__rf.fit(self.__X_train, self.__y_train)


    def calculate_metrics(self):
        out = []
        y_pred = self.__rf.predict(self.__X_test)

        c_matrix = confusion_matrix(self.__y_test, y_pred, labels=[1,2])

        out.append("Confusion Matrix: ")
        out.append(c_matrix)
        out.append("Accuracy:  " + str(accuracy_score(self.__y_test, y_pred)))
        out.append("Precision: " + str(precision_score(self.__y_test, y_pred)))
        out.append("Recall:    " + str(recall_score(self.__y_test, y_pred)))
        out.append("F1 Score:  " + str(f1_score(self.__y_test, y_pred)))

        # out.append(self.__rf.feature_importances_)
        return out


    def get_feature_importances(self):
        return self.__rf.feature_importances_


    def get_feature_names(self):
        return tuple(self.feature_names)


    def set_feature_names(self, feature_names):
        self.feature_names = feature_names


    def predict_an_image(self, input_image, output_image):
        dataset = gdal.Open(input_image, gdal.GA_ReadOnly)
        img_to_predict = np.zeros((dataset.RasterYSize, dataset.RasterXSize, dataset.RasterCount), dtype=np.float32)
        for band_number in range(dataset.RasterCount):
            band = dataset.GetRasterBand(band_number + 1)
            # Read in the band's data into the third dimension of our array
            img_to_predict[:, :, band_number] = band.ReadAsArray()

        new_shape = (img_to_predict.shape[0] * img_to_predict.shape[1], img_to_predict.shape[2])
        img_as_array = (img_to_predict[:, :, :dataset.RasterCount].reshape(new_shape))
        print('Reshaped from {old_shape} to {new_shape}'.format(
            old_shape=img_to_predict.shape, new_shape=img_as_array.shape))

        # Predicts for each pixel
        print("Predicting image...")
        class_prediction = self.__rf.predict(img_as_array)

        # Reshape classification map
        class_prediction = (class_prediction.reshape(img_to_predict[:, :, 0].shape))

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


    def export_classifier(self, pkl_filename):
        # Creates a new file that stores the classifier
        with open(pkl_filename, 'wb') as file:
            pickle.dump((self.__rf, self.feature_names), file, protocol=pickle.HIGHEST_PROTOCOL)


    def import_classifier(self, pkl_filename):
        # Loads a saved classifier
        with open(pkl_filename, 'rb') as file:
            self.__rf, self.feature_names = pickle.load(file)
