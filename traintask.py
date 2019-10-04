from .main import *

class ClassificationTask(PreProcessTask):
    def __init__(self, description, task):
        super().__init__(description, task)


    def rasterize_vector_files(self, places):
        for place in places:
            rasterized_vector_file = place.vector_file_path[:-4] + ".tif"
            print("Creating ROI: " + rasterized_vector_file)

            # Rasterize
            tiff_dataset = gdal.Open(
                place.extension_file_path, gdal.GA_ReadOnly)
            memory_driver = gdal.GetDriverByName('GTiff')
            if os.path.exists(rasterized_vector_file):
                os.remove(rasterized_vector_file)
            out_raster_ds = memory_driver.Create(
                rasterized_vector_file, tiff_dataset.RasterXSize,
                tiff_dataset.RasterYSize, 1, gdal.GDT_Byte)

            # Set the ROI image's projection and extent to the ones of the input
            out_raster_ds.SetProjection(tiff_dataset.GetProjectionRef())
            out_raster_ds.SetGeoTransform(tiff_dataset.GetGeoTransform())
            tiff_dataset = None

            # Fill output band with the 0 blank, no class label, value
            b = out_raster_ds.GetRasterBand(1)
            b.Fill(0)

            vector_dataset = ogr.Open(place.vector_file_path)
            layer = vector_dataset.GetLayerByIndex(0)
            # Rasterize the shapefile layer to our new dataset
            status = gdal.RasterizeLayer(
                out_raster_ds, [1], layer, None, None, [0],
                ['ALL_TOUCHED=TRUE', 'ATTRIBUTE=id'])

            # Close dataset
            out_raster_ds = None
            if status != 0:
                print("Error creating rasterized tiff")


    def stack_features(self, rasterized_file_path, files, file_name_stack):
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


class TrainTask(ClassificationTask):
    STACK_SUFFIX = "stack.csv"

    def __init__(self, directory, features,
                 classifier, lumberjack_instance):
        super().__init__("Lumberjack training", QgsTask.CanCancel)

        self.directory = directory
        self.features = features
        self.classifier = classifier
        self.li = lumberjack_instance

        self.classes = None
        self.exception = None


    def add_samples(self, file_name_stack):
        self.classifier.add_training_samples(file_name_stack)


    def run(self):
        try:
            QgsMessageLog.logMessage('Started task "{}"'.format(
                self.description()), PreProcessTask.MESSAGE_CATEGORY, Qgis.Info)

            self.start_time_str = str(datetime.datetime.now())
            print("=" * 30 + self.start_time_str + "=" * 30)
            self.start_time = time.time()

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
                    self.stack_features(place.vector_file_path[:-4]+".tif", files, file_name_stack)

            self.check_classes(places)
            # Add samples to train
            for place in places:
                for image in place.images:
                    file_name_stack = "{}/{}_sr_{}_{}".format(
                        image.path, image.base_name, "{}", TrainTask.STACK_SUFFIX)
                    self.add_samples(file_name_stack)

            self.classifier.fit(0)

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
                'Training Directory: {td}'.format(
                    name=self.description(),
                    time=self.elapsed_time,
                    td=self.directory),
                PreProcessTask.MESSAGE_CATEGORY, Qgis.Success)

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
                    PreProcessTask.MESSAGE_CATEGORY, Qgis.Warning)
            else:
                QgsMessageLog.logMessage(
                    'Task "{name}" Exception: {exception}'.format(
                        name=self.description(),
                        exception=self.exception),
                    PreProcessTask.MESSAGE_CATEGORY, Qgis.Critical)
                raise self.exception


class TestTask(ClassificationTask):
    def __init__(self, directory, features,
                 classifier, lumberjack_instance):
        super().__init__("Lumberjack testing", QgsTask.CanCancel)

        self.directory = directory
        self.features = features
        self.classifier = classifier
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

            places = self.obtain_places(self.directory)

            self.rasterize_vector_files(places)
            self.pre_process_images(places)

            self.check_classes(places)
            # Add samples to train
            for place in places:
                for image in place.images:
                    file_name_stack = "{}/{}_sr_{}_{}".format(
                        image.path, image.base_name, "{}", TrainTask.STACK_SUFFIX)
                    self.add_samples(file_name_stack)

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
