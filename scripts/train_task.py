from .preprocess_task import *
from .classification_task import *


class TrainTask(ClassificationTask):
    def __init__(self, directory, classifier,
                 testing_ratio, features, lumberjack_instance):
        super().__init__("Lumberjack training", QgsTask.CanCancel)
        self.directory = directory
        self.classifier = classifier
        self.without_ratio = testing_ratio
        self.features = features
        self.li = lumberjack_instance
        self.classes = None
        self.exception = None


    def add_samples(self, X, y):
        self.classifier.add_training_samples(X, y)


    def run(self):
        try:
            QgsMessageLog.logMessage('Started task "{}"'.format(
                self.description()), Lumberjack.MESSAGE_CATEGORY, Qgis.Info)
            self.start_time_str = str(datetime.datetime.now())
            print("=" * 30 + self.start_time_str + "=" * 30)
            self.start_time = time.time()

            places = self.obtain_places(self.directory)

            self.rasterize_vector_files(places)

            self.check_classes(places)

            # Add samples to train
            self.filter_samples(places)

            for feature in self.features:
                self.classifier.add_feature_names(feature.feature_names)

            # Defines to train with the whole set or if it has to be split
            if self.without_ratio:
                self.classifier.fit(0.0)
            else:
                self.classifier.fit(0.25)

            self.elapsed_time = time.time() - self.start_time
            print("Finished training in {} seconds".format(
                str(self.elapsed_time)))

            if self.isCanceled():
                return False
            return True

        except Exception as e:
            self.exception = e
            return False


    def finished(self, result):
        if result:
            QgsMessageLog.logMessage(
                'Task "{name}" completed in {time} seconds\n' \
                'Training Directory: {td}'.format(
                    name=self.description(),
                    time=self.elapsed_time,
                    td=self.directory),
                Lumberjack.MESSAGE_CATEGORY, Qgis.Success)

            self.li.notify_training(
                self.start_time_str, self.classes, self.total_samples,
                self.elapsed_time)

        else:
            if self.exception is None:
                QgsMessageLog.logMessage(
                    'Task "{name}" not successful but without '\
                    'exception (probably the task was manually '\
                    'canceled by the user)'.format(
                        name=self.description()),
                    Lumberjack.MESSAGE_CATEGORY, Qgis.Warning)
            else:
                QgsMessageLog.logMessage(
                    'Task "{name}" Exception: {exception}'.format(
                        name=self.description(),
                        exception=self.exception),
                    Lumberjack.MESSAGE_CATEGORY, Qgis.Critical)
                raise self.exception
