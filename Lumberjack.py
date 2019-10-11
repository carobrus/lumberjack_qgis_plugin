# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Lumberjack
                                 A QGIS plugin
 This plugin calculates features of images, classifies and removes trees out
    of elevation maps
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2019-07-01
        git sha              : $Format:%H$
        copyright            : (C) 2019 by UNICEN
        email                : bruscantinic@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QFileDialog
from qgis.utils import iface
from qgis.core import Qgis
from qgis.core import (QgsApplication, QgsTask, QgsMessageLog, QgsProject)

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .Lumberjack_dialog import LumberjackDialog
import os.path

from .scripts.train_task import TrainTask
from .scripts.test_task import TestTask
from .scripts.predict_task import PredictTask
from .scripts.classifier import Classifier
from .scripts.features import AlgebraFeature, FilterFeature, FilterGaussFeature, NdviFeature, DayFeature
from .scripts.seasonal_analysis import CalculateFeaturesTask, SeasonalAnalysis
from .scripts.tree_correction import TreeCorrectionTask

import sys

from .scripts.plot import PlotWindow
from .scripts.plotbox import PlotWindow as PlotboxWindow

MESSAGE_CATEGORY = 'Lumberjack'

class Lumberjack:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'Lumberjack_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Lumberjack')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None
        self.train_task = None
        self.test_task = None
        self.predict_task = None
        self.classifier = None
        self.features = None
        self.testing_ratio = None
        self.include_textures_image = None
        self.include_textures_places = None
        self.calculate_features_task = None
        self.tree_correction_task = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('Lumberjack', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/Lumberjack/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Detect Trees'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Lumberjack'),
                action)
            self.iface.removeToolBarIcon(action)

    def select_training_directory(self):
        filename = QFileDialog.getExistingDirectory(
            self.dlg, "Select training directory","")
        self.dlg.lineEdit_trainingDirectory.setText(filename)

    def select_prediction_directory(self):
        filename = QFileDialog.getExistingDirectory(
            self.dlg, "Select prediction directory","")
        self.dlg.lineEdit_predictionDirectoy.setText(filename)

    def select_testing_directory(self):
        filename = QFileDialog.getExistingDirectory(
            self.dlg, "Select training directory","")
        self.dlg.lineEdit_testingDirectory.setText(filename)

    def select_seasonal_directory(self):
        filename = QFileDialog.getExistingDirectory(
            self.dlg, "Select directory","")
        self.dlg.lineEdit_directory_seasonal.setText(filename)

    def select_mask(self):
        filename = QFileDialog.getOpenFileName(self.dlg, "Select mask","","*.tif; *.tiff")
        self.dlg.lineEdit_mask_file.setText(filename[0])

    def search_dem(self):
        filename = QFileDialog.getOpenFileName(self.dlg, "Select dem","","*.tif; *.tiff")
        self.dlg.lineEdit_dem.setText(filename[0])

    def search_tree_mask(self):
        filename = QFileDialog.getOpenFileName(self.dlg, "Select tree mask","","*.tif; *.tiff")
        self.dlg.lineEdit_tree_mask.setText(filename[0])

    def search_output_dem(self):
        filename = QFileDialog.getSaveFileName(self.dlg, "Select output file ","","*.tif; *.tiff")
        self.dlg.lineEdit_output_dem.setText(filename[0])

    def run(self):
        """Run method that performs all the real work"""
        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback,
        # so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = LumberjackDialog()

            self.dlg.lineEdit_trainingDirectory.clear()
            self.dlg.pushButton_trainingDirectory.clicked.connect(
                self.select_training_directory)

            self.dlg.lineEdit_predictionDirectoy.clear()
            self.dlg.pushButton_predictionDirectory.clicked.connect(
                self.select_prediction_directory)

            self.dlg.lineEdit_testingDirectory.clear()
            self.dlg.pushButton_testingDirectory.clicked.connect(
                self.select_testing_directory)

            self.dlg.pushButton_training.clicked.connect(self.train)
            self.dlg.pushButton_testing.clicked.connect(self.test)
            self.dlg.pushButton_prediction.clicked.connect(self.predict)

            self.dlg.pushButton_seasonal.clicked.connect(
                self.select_seasonal_directory)

            self.dlg.pushButton_mask.clicked.connect(self.select_mask)

            self.dlg.pushButton_calculate_features.clicked.connect(
                self.calculate_features)
            self.dlg.pushButton_boxplot.clicked.connect(
                self.plot_seasonal_analysis)

            self.dlg.pushButton_search_dem.clicked.connect(self.search_dem)
            self.dlg.pushButton_search_tree_mask.clicked.connect(self.search_tree_mask)
            self.dlg.pushButton_output_dem.clicked.connect(self.search_output_dem)

            self.dlg.pushButton_correct_trees.clicked.connect(self.correct_trees)

            self.dlg.tabWidget.setCurrentIndex(0)

        self.dlg.open()


    def correct_trees(self):
        self.tree_correction_task = TreeCorrectionTask(
            dem_file = self.dlg.lineEdit_dem.text(),
            tree_mask_file = self.dlg.lineEdit_tree_mask.text(),
            output_file = self.dlg.lineEdit_output_dem.text(),
            dilate_amount = self.dlg.spinBox_dilation.value(),
            lumberjack_instance = self
        )
        QgsApplication.taskManager().addTask(self.tree_correction_task)


    def notify_tree_correction(self, start_time, output_file, time):
        self.dlg.plainTextEdit.appendPlainText("======== {} ========".format(str(start_time)))
        self.dlg.plainTextEdit.appendPlainText("Finished tree correction in {} seconds".format(str(time)))
        if self.dlg.checkBox_add_dem.isChecked():
            file_name = output_file.split("/")[-1]
            self.iface.addRasterLayer(output_file, file_name)
            layers = QgsProject.instance().mapLayersByName(file_name)
        self.iface.messageBar().pushMessage("Success", "Output file {} created".format(file_name), level=Qgis.Success, duration=5)


    def calculate_features(self):
        self.dlg.hide()
        self.features = []
        if self.dlg.checkBox_bandsAlgebra.isChecked():
            self.features.append(AlgebraFeature())
        if self.dlg.checkBox_medianFilter.isChecked():
            self.features.append(FilterFeature())
            self.features.append(FilterGaussFeature())
        if self.dlg.checkBox_ndvi.isChecked():
            self.features.append(NdviFeature())
        if self.dlg.checkBox_dem.isChecked():
            self.features.append(DayFeature())

        self.calculate_features_task = CalculateFeaturesTask(
            directory = self.dlg.lineEdit_directory_seasonal.text(),
            features = self.features,
            include_textures_image = self.dlg.checkBox_textures.isChecked(),
            include_textures_places = self.dlg.checkBox_dem.isChecked(),
            lumberjack_instance = self)
        QgsApplication.taskManager().addTask(self.calculate_features_task)


    def plot_seasonal_analysis(self):
        self.dlg.hide()
        self.seasonal_analysis = SeasonalAnalysis(
            directory = self.dlg.lineEdit_directory_seasonal.text(),
            mask_layer_file = self.dlg.lineEdit_mask_file.text(),
            feature = self.dlg.spinBox_feature.value(),
            lumberjack_instance = self)
        QgsApplication.taskManager().addTask(self.seasonal_analysis)


    def notify_calculate_features(self, start_time, range, time):
        self.dlg.spinBox_feature.setRange(1, range)
        self.dlg.plainTextEdit.appendPlainText("======== {} ========".format(str(start_time)))
        self.dlg.plainTextEdit.appendPlainText("Finished features in {} seconds".format(str(time)))
        # self.dlg.open()


    def notify_seasonal_analysis(self, start_time, data, days, time):
        self.dlg.open()
        self.dlg.plainTextEdit.appendPlainText("======== {} ========".format(str(start_time)))
        self.dlg.plainTextEdit.appendPlainText("Finished in {} seconds".format(str(time)))
        self.plotboxWindow = PlotboxWindow(self.dlg, data=data, days=days)
        self.plotboxWindow.show()


    def train(self):
        self.dlg.hide()
        self.features = []
        if self.dlg.checkBox_bandsAlgebra.isChecked():
            self.features.append(AlgebraFeature())
        if self.dlg.checkBox_medianFilter.isChecked():
            self.features.append(FilterFeature())
            self.features.append(FilterGaussFeature())
        if self.dlg.checkBox_ndvi.isChecked():
            self.features.append(NdviFeature())
        if self.dlg.checkBox_dem.isChecked():
            self.features.append(DayFeature())

        self.classifier = Classifier()
        self.testing_ratio = self.dlg.checkBox_testing_ratio.isChecked()
        self.include_textures_image = self.dlg.checkBox_textures.isChecked()
        self.include_textures_places = self.dlg.checkBox_dem.isChecked()

        self.train_task = TrainTask(
            directory = self.dlg.lineEdit_trainingDirectory.text(),
            features = self.features,
            classifier = self.classifier,
            testing_ratio = self.testing_ratio,
            include_textures_image = self.include_textures_image,
            include_textures_places = self.include_textures_places,
            lumberjack_instance = self)
        QgsApplication.taskManager().addTask(self.train_task)

        self.dlg.pushButton_testing.setEnabled(True)
        self.dlg.pushButton_prediction.setEnabled(True)


    def test(self):
        self.dlg.hide()
        self.test_task = TestTask(
            directory = self.dlg.lineEdit_testingDirectory.text(),
            features = self.features,
            classifier = self.classifier,
            testing_ratio = self.testing_ratio,
            include_textures_image = self.include_textures_image,
            include_textures_places = self.include_textures_places,
            lumberjack_instance = self)
        QgsApplication.taskManager().addTask(self.test_task)


    def predict(self):
        self.dlg.hide()
        self.calculate_features_task = CalculateFeaturesTask(
            directory = self.dlg.lineEdit_predictionDirectoy.text(),
            features = self.features,
            include_textures_image = self.include_textures_image,
            include_textures_places = self.include_textures_places,
            lumberjack_instance = self)

        self.predict_task = PredictTask(
            directory = self.dlg.lineEdit_predictionDirectoy.text(),
            classifier = self.classifier,
            lumberjack_instance = self)

        self.predict_task.addSubTask(self.calculate_features_task, [], QgsTask.ParentDependsOnSubTask)
        QgsApplication.taskManager().addTask(self.predict_task)


    def notify_training(self, start_time, classes, total_samples, time):
        self.dlg.plainTextEdit.appendPlainText("======== {} ========".format(str(start_time)))
        self.dlg.plainTextEdit.appendPlainText("Classes when training:")
        for i in classes:
            self.dlg.plainTextEdit.appendPlainText("- " + str(i))
        self.dlg.plainTextEdit.appendPlainText("Total samples: {}".format(str(total_samples)))
        self.dlg.plainTextEdit.appendPlainText("Finished in {} seconds".format(str(time)))
        self.dlg.plainTextEdit.appendPlainText("")

        self.dlg.open()


    def notify_testing(self, start_time, classes, total_samples, metrics, time):
        self.dlg.plainTextEdit.appendPlainText("======== {} ========".format(str(start_time)))
        if (not classes is None):
            self.dlg.plainTextEdit.appendPlainText("Classes when testing:")
            for i in classes:
                self.dlg.plainTextEdit.appendPlainText("- " + str(i))
        self.dlg.plainTextEdit.appendPlainText("Total samples: {}".format(str(total_samples)))

        for i in metrics[:-1]:
            self.dlg.plainTextEdit.appendPlainText(str(i))
        self.dlg.plainTextEdit.appendPlainText("Finished in {} seconds".format(str(time)))
        self.dlg.plainTextEdit.appendPlainText("")

        self.dlg.open()

        # Barchart window with feature importances
        self.plotWindow = PlotWindow(self.dlg, feature_importances=metrics[-1])
        self.plotWindow.show()


    def notify_prediction(self, start_time, output_files, time):
        self.dlg.plainTextEdit.appendPlainText("======== {} ========".format(str(start_time)))
        self.dlg.plainTextEdit.appendPlainText("Finished prediction in {} seconds".format(str(time)))
        self.iface.messageBar().pushMessage("Success", "Output file/s created", level=Qgis.Success, duration=5)
        if self.dlg.checkBox_addFile.isChecked():
            for file_path in output_files:
                file_name = file_path.split("/")[-1]
                self.iface.addRasterLayer(file_path, file_name)
                layers = QgsProject.instance().mapLayersByName(file_name)
                abs_style_path = self.plugin_dir + "/prediction_tree_style.qml"
                layers[0].loadNamedStyle(abs_style_path)
                self.iface.layerTreeView().refreshLayerSymbology(layers[0].id())
