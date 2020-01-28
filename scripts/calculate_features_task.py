import os
from osgeo import gdal
import numpy as np
import time
import datetime
from .preprocess_task import *
from .. import Lumberjack


class CalculateFeaturesTask(PreProcessTask):
    def __init__(self, directory, features, lumberjack_instance):
        super().__init__("Calculate Features Task", QgsTask.CanCancel)
        self.directory = directory
        self.features = features
        self.lumberjack_instance = lumberjack_instance
        self.feature_names = []


    def run(self):
        try:
            QgsMessageLog.logMessage('Started task "{}"'.format(
                self.description()), Lumberjack.MESSAGE_CATEGORY, Qgis.Info)
            self.start_time_str = str(datetime.datetime.now())
            print("=" * 30 + self.start_time_str + "=" * 30)
            self.start_time = time.time()

            places = self.obtain_places(self.directory)
            self.pre_process_images(places)

            for place in places:
                for image in place.images:
                    file_name_stack = os.path.join(
                        image.path, "{}{}".format(
                            image.base_name, Lumberjack.STACK_SUFFIX))
                    
                    files = []
                    for feature in self.features:
                        files.append(feature.get_file_name(image))

                    self.total_features = self.calculate_total_features(files)
                    self.merge_images(files, file_name_stack, self.total_features, gdal.GDT_Float32)
            
            for feature in self.features:
                self.feature_names.extend(feature.feature_names)

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
            self.lumberjack_instance.notify_calculate_features(
                self.start_time_str, self.total_features,
                self.feature_names, self.directory, self.elapsed_time)
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
