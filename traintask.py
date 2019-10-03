from .main import *

class TrainTask(Main):

    def __init__(self, training_directory, features,
                 do_testing, testing_directory,
                 do_prediction, prediction_directory, lumberjack_instance):
        super().__init__("Lumberjack training", QgsTask.CanCancel)

        self.training_directory = training_directory
        self.do_testing = do_testing
        self.testing_directory = testing_directory
        self.do_prediction = do_prediction
        self.prediction_directory = prediction_directory
        self.li = lumberjack_instance

        self.exception = None
        self.output_files = []
        self.classes = None
        self.features = features

    def filter_features(self, rasterized_file_path, files, file_name_stack):
        roi_dataset = gdal.Open(rasterized_file_path, gdal.GA_ReadOnly)
        roi = roi_dataset.GetRasterBand(1).ReadAsArray().astype(np.uint8)

        total_features = self.calculate_total_features(files)

        features_array = np.zeros(
            (roi_dataset.RasterYSize, roi_dataset.RasterXSize, total_features),
            dtype=np.float32)
        print("Shape array features: {}".format(features_array.shape))

        band_acum = 0
        for file in files:
            dataset = gdal.Open(file, gdal.GA_ReadOnly)
            for band_number in range(dataset.RasterCount):
                band = dataset.GetRasterBand(band_number + 1)
                features_array[:, :, band_acum] = band.ReadAsArray()
                band_acum += 1

        X = features_array[roi > 0, :]
        y = roi[roi > 0]

        print("X size: {}".format(X.shape))
        print("y size: {}".format(y.shape))

        # Create the file X and y that's going to stack all the features and labels
        if os.path.exists(file_name_stack.format("X")):
            os.remove(file_name_stack.format("X"))
        if os.path.exists(file_name_stack.format("y")):
            os.remove(file_name_stack.format("y"))

        np.savetxt(file_name_stack.format("X"), X, delimiter=",")
        np.savetxt(file_name_stack.format("y"), y, delimiter=",")


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
                self.classes.append('Class {c} contains {n} pixels'.format(
                    c=c, n=(roi == c).sum()))

            # Find how many non-zero entries there are
            n_samples = (roi > 0).sum()
            self.total_samples = self.total_samples + n_samples * len(place.images)
            self.classes.append('There are {n} samples'.format(n=n_samples))


    def run(self):
        try:
            QgsMessageLog.logMessage('Started task "{}"'.format(
                self.description()), Main.MESSAGE_CATEGORY, Qgis.Info)

            self.start_time_str = str(datetime.datetime.now())
            print("=" * 30 + self.start_time_str + "=" * 30)
            self.start_time = time.time()

            places_training = self.obtain_places(self.training_directory)

            self.rasterize_vector_files(places_training)
            self.pre_process_images(places_training)

            # Create classifier and add samples to train
            classifier = Classifier()
            self.check_classes(places_training)
            for place in places_training:
                for image in place.images:
                    file_name_stack = "{}/{}_sr_{}_{}".format(
                        image.path, image.base_name, "{}", STACK_SUFFIX)
                    classifier.add_training_samples(file_name_stack)

            self.elapsed_time = time.time() - self.start_time
            print("Finished training in {} seconds".format(str(self.elapsed_time)))

            if self.isCanceled():
                return False

            self.setProgress(100)
            return True

        except Exception as e:
            self.exception = e
            return False


    def finished(self, result):
        if result:
            QgsMessageLog.logMessage(
                'Task "{name}" completed in {time} seconds\n' \
                'Training Directory: {td})'.format(
                    name=self.description(),
                    time=self.elapsed_time,
                    td=self.training_directory),
                Main.MESSAGE_CATEGORY, Qgis.Success)

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
                    Main.MESSAGE_CATEGORY, Qgis.Warning)
            else:
                QgsMessageLog.logMessage(
                    'Task "{name}" Exception: {exception}'.format(
                        name=self.description(),
                        exception=self.exception),
                    Main.MESSAGE_CATEGORY, Qgis.Critical)
                raise self.exception
