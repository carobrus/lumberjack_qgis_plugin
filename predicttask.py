from .main import *

class PredictTask(PreProcessTask):
    PREDICTION_SUFFIX = "predic.tif"
    STACK_SUFFIX = "stack.tif"


    def __init__(self):
        super().__init__("Lumberjack testing", QgsTask.CanCancel)


    def run(self):
        pass


    def finished(self, result):
        pass


    def predict(self, places, classifier, time_stamp):
        output_files = []
        for place in places:
            for image in place.images:
                stack_file_name = "{}/{}_sr_{}_{}".format(
                    image.path, image.base_name, "{}", PredictTask.STACK_SUFFIX)
                output_file = "{}/{}_sr_{}_{}".format(
                    image.path, image.base_name, PredictTask.PREDICTION_SUFFIX,
                    time_stamp.replace(" ", "_").replace(":","-"))
                output_files.append(output_file)
                classifier.predict_an_image(stack_file_name, output_file)
        return output_files
