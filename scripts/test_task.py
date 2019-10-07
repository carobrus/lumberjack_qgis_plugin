from .preprocess_task import *
from .classification_task import *

class TestTask(ClassificationTask):
    def __init__(self, directory, features,
                 classifier, testing_ratio, include_textures_image,
                 include_textures_places, lumberjack_instance):
        super().__init__("Lumberjack testing", QgsTask.CanCancel)

        self.directory = directory
        self.features = features
        self.classifier = classifier
        self.without_ratio = testing_ratio
        self.include_textures_image = include_textures_image
        self.include_textures_places = include_textures_places
        self.li = lumberjack_instance

        self.classes = None
        self.exception = None


    def add_samples(self, file_name_stack):
        self.classifier.add_testing_samples(file_name_stack)


    def run(self):
        try:
            QgsMessageLog.logMessage('Started task "{}"'.format(
                self.description()), PreProcessTask.MESSAGE_CATEGORY, Qgis.Info)
            self.start_time_str = str(datetime.datetime.now())
            print("=" * 30 + self.start_time_str + "=" * 30)
            self.start_time = time.time()

            if self.without_ratio:
                places = self.obtain_places(self.directory)

                self.rasterize_vector_files(places)
                self.pre_process_images(places)

                for place in places:
                    for image in place.images:
                        file_name_stack = "{}/{}_sr_{}_{}".format(
                            image.path, image.base_name, "{}", TrainTask.STACK_SUFFIX)
                        file_merged = "{}/{}_sr_{}".format(image.path, image.base_name, MERGED_SUFFIX)
                        files = [file_merged]
                        for feature in self.features:
                            files.append(feature.file_format.format(file_merged[:-4]))
                        # add textures
                        if self.include_textures_image:
                            files.append(image.extra_features)
                        if self.include_textures_places:
                            files.append(place.dem_textures_file_path)
                        self.stack_features(place.vector_file_path[:-4]+".tif", files, file_name_stack)

                self.check_classes(places)
                # Add samples to train
                for place in places:
                    for image in place.images:
                        file_name_stack = "{}/{}_sr_{}_{}".format(
                            image.path, image.base_name, "{}", TrainTask.STACK_SUFFIX)
                        self.add_samples(file_name_stack)
            else:
                self.total_samples = self.classifier.get_test_size()
            self.metrics = self.classifier.calculate_metrics()

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
                    PreProcessTask.MESSAGE_CATEGORY, Qgis.Warning)
            else:
                QgsMessageLog.logMessage(
                    'Task "{name}" Exception: {exception}'.format(
                        name=self.description(),
                        exception=self.exception),
                    PreProcessTask.MESSAGE_CATEGORY, Qgis.Critical)
                raise self.exception
