from .preprocess_task import *

class PredictTask(PreProcessTask):
    PREDICTION_SUFFIX = "predic.tif"
    STACK_SUFFIX = "stack.tif"


    def __init__(self, directory, classifier, lumberjack_instance):
        super().__init__("Lumberjack prediction", QgsTask.CanCancel)
        self.directory = directory
        self.classifier = classifier
        self.li = lumberjack_instance
        self.output_files = []


    def run(self):
        try:
            QgsMessageLog.logMessage('Started task "{}"'.format(
                self.description()), PreProcessTask.MESSAGE_CATEGORY, Qgis.Info)

            self.start_time_str = str(datetime.datetime.now())
            print("=" * 30 + self.start_time_str + "=" * 30)
            self.start_time = time.time()

            places = self.obtain_places(self.directory)

            self.output_files = []
            for place in places:
                for image in place.images:
                    file_name_stack = "{}/{}_sr_{}".format(
                        image.path, image.base_name, PredictTask.STACK_SUFFIX)
                    time_stamp = self.start_time_str[:19]
                    output_file = "{}/{}_sr_{}_{}".format(
                        image.path, image.base_name, PredictTask.PREDICTION_SUFFIX,
                        time_stamp.replace(" ", "_").replace(":","-"))
                    self.output_files.append(output_file)
                    self.classifier.predict_an_image(file_name_stack, output_file)

            self.elapsed_time = time.time() - self.start_time
            print("Finished training in {} seconds".format(str(self.elapsed_time)))

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
                PreProcessTask.MESSAGE_CATEGORY, Qgis.Success)

            self.li.notify_prediction(
                self.start_time_str, self.output_files, self.elapsed_time)

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
