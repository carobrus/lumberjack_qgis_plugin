from osgeo import gdal
import numpy as np
import time
import datetime
from .preprocess_task import *
from .. import Lumberjack


class SeasonalAnalysis(PreProcessTask):
    def __init__(self, directory, feature, lumberjack_instance):
        super().__init__("Seasonal Analysis", QgsTask.CanCancel)
        self.directory = directory
        self.feature_number = feature
        self.lumberjack_instance = lumberjack_instance


    def transform_day(self, date):
        year, month, day = date.split("-")
        year = int(year)
        month = int(month)
        day = int(day)
        number_of_day = (datetime.date(year, month, day) - datetime.date(year, 1, 1)).days + 1
        return number_of_day


    def get_date_from_metadata(self, file):
        with open(file, 'r') as f:
            for line in f.readlines():
                if "DATE_ACQUIRED =" in line:
                    l = line.split("=")
                    return l[1]


    def calculate_threshold(self):
        places = self.obtain_places(self.directory)

        self.days = []
        self.data = []
        for place in places:
            if (place.mask != ""):
                mask = gdal.Open(place.mask, gdal.GA_ReadOnly)
                mask_array = mask.GetRasterBand(1).ReadAsArray().astype(np.uint8)

                stack_files = []
                for image in place.images:
                    file_name_stack = os.path.join(
                        image.path, 
                        "{}{}".format(image.base_name, Lumberjack.STACK_SUFFIX))
                    stack_files.append([file_name_stack, image.metadata_file])

                for i, file in enumerate(stack_files):
                    features = gdal.Open(file[0], gdal.GA_ReadOnly)
                    band = features.GetRasterBand(self.feature_number)

                    date = self.get_date_from_metadata(file[1])
                    number_of_day = self.transform_day(date)

                    print("Working on image of day: {}".format(number_of_day))
                    self.days.append(number_of_day)
                    self.data.append(band.ReadAsArray()[mask_array < 2])


    def run(self):
        try:
            QgsMessageLog.logMessage('Started task "{}"'.format(
                self.description()), Lumberjack.MESSAGE_CATEGORY, Qgis.Info)
            self.start_time_str = str(datetime.datetime.now())
            print("=" * 30 + self.start_time_str + "=" * 30)
            self.start_time = time.time()

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
            'Task "{name}" was canceled'.format(name=self.description()),
            Lumberjack.MESSAGE_CATEGORY, Qgis.Info)
        super().cancel()


    def finished(self, result):
        if result:
            QgsMessageLog.logMessage(
                'Task "{name}" completed in {time} seconds\n' \
                'Directory: {td}'.format(name=self.description(), time=self.elapsed_time, td=self.directory),
                Lumberjack.MESSAGE_CATEGORY, Qgis.Success)
            self.lumberjack_instance.notify_seasonal_analysis(
                self.start_time_str, self.data, self.days, self.elapsed_time)
        else:
            if self.exception is None:
                QgsMessageLog.logMessage(
                    'Task "{name}" not successful but without '\
                    'exception (probably the task was manually '\
                    'canceled by the user)'.format(name=self.description()),
                    Lumberjack.MESSAGE_CATEGORY, Qgis.Warning)
            else:
                QgsMessageLog.logMessage(
                    'Task "{name}" Exception: {exception}'.format(name=self.description(), exception=self.exception),
                    Lumberjack.MESSAGE_CATEGORY, Qgis.Critical)
                raise self.exception
