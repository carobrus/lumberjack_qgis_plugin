from osgeo import gdal
import numpy as np
import time
import datetime
from .preprocess_task import *

class CalculateFeaturesTask(PreProcessTask):
    def __init__(self, directory, features, include_textures_image,
                 include_textures_places, lumberjack_instance):
        super().__init__("Calculate Features Task", QgsTask.CanCancel)
        self.directory = directory
        self.features = features
        self.include_textures_image = include_textures_image
        self.include_textures_places = include_textures_places
        self.lumberjack_instance = lumberjack_instance


    def run(self):
        try:
            QgsMessageLog.logMessage('Started task "{}"'.format(
                self.description()), PreProcessTask.MESSAGE_CATEGORY, Qgis.Info)
            self.start_time_str = str(datetime.datetime.now())
            print("=" * 30 + self.start_time_str + "=" * 30)
            self.start_time = time.time()

            places = self.obtain_places(self.directory)
            self.pre_process_images(places)

            for place in places:
                for image in place.images:
                    file_name_stack = "{}/{}_sr_{}".format(
                        image.path, image.base_name, "stack.tif")
                    file_merged = "{}/{}_sr_{}".format(image.path, image.base_name, MERGED_SUFFIX)
                    files = [file_merged]
                    for feature in self.features:
                        files.append(feature.file_format.format(file_merged[:-4]))
                    # add textures
                    if self.include_textures_image:
                        files.append(image.extra_features)
                    if self.include_textures_places:
                        files.append(place.dem_textures_file_path)
                    self.total_features = self.calculate_total_features(files)
                    self.merge_images(files, file_name_stack, self.total_features, gdal.GDT_Float32)

            self.elapsed_time = time.time() - self.start_time
            print("Finished in {} seconds".format(str(self.elapsed_time)))

            if self.isCanceled():
                return False
            return True

        except Exception as e:
            self.exception = e
            return False


    def cancel(self):
        QgsMessageLog.logMessage(
            'Task "{name}" was canceled'.format(
                name=self.description()),
            Main.MESSAGE_CATEGORY, Qgis.Info)
        super().cancel()


    def finished(self, result):
        if result:
            QgsMessageLog.logMessage(
                'Task "{name}" completed in {time} seconds\n' \
                'Directory: {td}'.format(
                    name=self.description(),
                    time=self.elapsed_time,
                    td=self.directory),
                PreProcessTask.MESSAGE_CATEGORY, Qgis.Success)
            self.lumberjack_instance.notify_calculate_features(
                self.start_time_str, self.total_features, self.elapsed_time)
        else:
            if self.exception is None:
                QgsMessageLog.logMessage(
                    'Task "{name}" not successful but without '\
                    'exception (probably the task was manually '\
                    'canceled by the user)'.format(
                        name=self.description()),
                    PreProcessTask.MESSAGE_CATEGORY, Qgis.Warning)
            else:
                QgsMessageLog.logMessage(
                    'Task "{name}" Exception: {exception}'.format(
                        name=self.description(),
                        exception=self.exception),
                    PreProcessTask.MESSAGE_CATEGORY, Qgis.Critical)
                raise self.exception


class SeasonalAnalysis(PreProcessTask):
    def __init__(self, directory, mask_layer_file, feature, lumberjack_instance):
        super().__init__("Seasonal Analysis", QgsTask.CanCancel)
        self.directory = directory
        self.mask_layer_file = mask_layer_file
        self.feature_number = feature
        self.lumberjack_instance = lumberjack_instance


    def transform_day(self, date):
        year, month, day = date.split("-")
        year = int(year)
        month = int(month)
        day = int(day)
        number_of_day = (datetime.date(year, month, day) -
                         datetime.date(year, 1, 1)).days + 1
        return number_of_day


    def get_date_from_metadata(self, file):
        f = open(file, 'r')
        for line in f.readlines():
            if "DATE_ACQUIRED =" in line:
                l = line.split("=")
                return l[1]


    def calculate_threshold(self):
        places = self.obtain_places(self.directory)

        self.days = []
        self.data = []
        files = []
        for place in places:
            for image in place.images:
                file_name_stack = "{}/{}_sr_{}".format(
                    image.path, image.base_name, "stack.tif")
                file_name_metadata = "{}/{}_{}".format(
                    image.path, image.base_name, "MTL.txt")
                files.append([file_name_stack, file_name_metadata])

        mask = gdal.Open(self.mask_layer_file, gdal.GA_ReadOnly)
        mask_array = mask.GetRasterBand(1).ReadAsArray().astype(np.uint8)
        band_arrays = np.zeros((mask.RasterYSize, mask.RasterXSize, len(files)), dtype=np.float32)

        for i, file in enumerate(files):
            features = gdal.Open(file[0], gdal.GA_ReadOnly)
            band = features.GetRasterBand(self.feature_number)
            # band_arrays[:, :, i] = band.ReadAsArray()

            date = self.get_date_from_metadata(file[1])
            number_of_day = self.transform_day(date)

            print("Working on image of day: {}".format(number_of_day))
            self.days.append(number_of_day)
            self.data.append(band.ReadAsArray()[mask_array < 2])

        # band_filtered = band_arrays[mask_array < 2, :]
        # return band_filtered, self.days


    def run(self):
        try:
            QgsMessageLog.logMessage('Started task "{}"'.format(
                self.description()), PreProcessTask.MESSAGE_CATEGORY, Qgis.Info)
            self.start_time_str = str(datetime.datetime.now())
            print("=" * 30 + self.start_time_str + "=" * 30)
            self.start_time = time.time()

            # self.data, self.days = self.calculate_threshold()
            self.calculate_threshold()

            self.elapsed_time = time.time() - self.start_time
            print("Finished in {} seconds".format(str(self.elapsed_time)))

            if self.isCanceled():
                return False
            return True

        except Exception as e:
            self.exception = e
            return False


    def cancel(self):
        QgsMessageLog.logMessage(
            'Task "{name}" was canceled'.format(
                name=self.description()),
            Main.MESSAGE_CATEGORY, Qgis.Info)
        super().cancel()


    def finished(self, result):
        if result:
            QgsMessageLog.logMessage(
                'Task "{name}" completed in {time} seconds\n' \
                'Directory: {td}'.format(
                    name=self.description(),
                    time=self.elapsed_time,
                    td=self.directory),
                PreProcessTask.MESSAGE_CATEGORY, Qgis.Success)
            self.lumberjack_instance.notify_seasonal_analysis(
                self.start_time_str, self.data, self.days, self.elapsed_time)
        else:
            if self.exception is None:
                QgsMessageLog.logMessage(
                    'Task "{name}" not successful but without '\
                    'exception (probably the task was manually '\
                    'canceled by the user)'.format(
                        name=self.description()),
                    PreProcessTask.MESSAGE_CATEGORY, Qgis.Warning)
            else:
                QgsMessageLog.logMessage(
                    'Task "{name}" Exception: {exception}'.format(
                        name=self.description(),
                        exception=self.exception),
                    PreProcessTask.MESSAGE_CATEGORY, Qgis.Critical)
                raise self.exception
