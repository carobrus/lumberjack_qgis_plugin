from .preprocess_task import *
from .classification_task import *
from .train_task import TrainTask


class TestTask(ClassificationTask):
    def __init__(self, directory, classifier, testing_ratio,
                 lumberjack_instance):
        super().__init__("Lumberjack testing", QgsTask.CanCancel)
        self.directory = directory
        self.classifier = classifier
        self.without_ratio = testing_ratio
        self.li = lumberjack_instance
        self.classes = None
        self.exception = None


    def add_samples(self, X, y):
        self.classifier.add_testing_samples(X, y)


    def run(self):
        try:
            QgsMessageLog.logMessage('Started task "{}"'.format(
                self.description()), Lumberjack.MESSAGE_CATEGORY, Qgis.Info)
            self.start_time_str = str(datetime.datetime.now())
            print("=" * 30 + self.start_time_str + "=" * 30)
            self.start_time = time.time()

            if self.without_ratio:
                # Stack the features to be used
                places = self.obtain_places(self.directory)

                self.rasterize_vector_files(places)

                self.check_classes(places)
                self.filter_samples(places)

            else:
                # No samples are added
                self.total_samples = self.classifier.get_test_size()

            # Calculates the metrics with the classifer already trained and
            # a testing set
            self.metrics = self.classifier.calculate_metrics()

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
                'Testing Directory: {td}'.format(
                    name=self.description(),
                    time=self.elapsed_time,
                    td=self.directory),
                Lumberjack.MESSAGE_CATEGORY, Qgis.Success)

            self.li.notify_testing(
                self.start_time_str, self.classes, self.total_samples,
                self.metrics, self.elapsed_time)

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
