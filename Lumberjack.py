# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Lumberjack
                                 A QGIS plugin
 This plugin calculates features of images, classifies and removes trees out of elevation maps
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

from .traintask import TrainTask
from .features import AlgebraFeature, FilterFeature, FilterGaussFeature, NdviFeature, DayFeature

import sys

from .plot import PlotWindow
from .plotbox import PlotWindow as PlotboxWindow

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
        filename = QFileDialog.getExistingDirectory(self.dlg, "Select training directory","")
        self.dlg.lineEdit_trainingDirectory.setText(filename)

    def select_prediction_directory(self):
        filename = QFileDialog.getExistingDirectory(self.dlg, "Select prediction directory","")
        self.dlg.lineEdit_predictionDirectoy.setText(filename)

    def select_testing_directory(self):
        filename = QFileDialog.getExistingDirectory(self.dlg, "Select training directory","")
        self.dlg.lineEdit_testingDirectory.setText(filename)

    def toggle_predicting_image(self, state):
        if state > 0:
            self.dlg.label_imageDirectory.setEnabled(True)
            self.dlg.lineEdit_predictionDirectoy.setEnabled(True)
            self.dlg.pushButton_predictionDirectory.setEnabled(True)
            self.dlg.checkBox_addFile.setEnabled(True)
        else:
            self.dlg.label_imageDirectory.setEnabled(False)
            self.dlg.lineEdit_predictionDirectoy.setEnabled(False)
            self.dlg.pushButton_predictionDirectory.setEnabled(False)
            self.dlg.checkBox_addFile.setEnabled(False)

    def toggle_testing(self, state):
        if state > 0:
            self.dlg.label_testingDirectory.setEnabled(True)
            self.dlg.lineEdit_testingDirectory.setEnabled(True)
            self.dlg.pushButton_testingDirectory.setEnabled(True)
        else:
            self.dlg.label_testingDirectory.setEnabled(False)
            self.dlg.lineEdit_testingDirectory.setEnabled(False)
            self.dlg.pushButton_testingDirectory.setEnabled(False)


    def run(self):
        """Run method that performs all the real work"""
        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = LumberjackDialog()

            self.dlg.lineEdit_trainingDirectory.clear()
            self.dlg.pushButton_trainingDirectory.clicked.connect(self.select_training_directory)

            self.dlg.checkBox_prediction.stateChanged.connect(self.toggle_predicting_image)

            self.dlg.lineEdit_predictionDirectoy.clear()
            self.dlg.pushButton_predictionDirectory.clicked.connect(self.select_prediction_directory)

            self.dlg.checkBox_testing.stateChanged.connect(self.toggle_testing)

            self.dlg.lineEdit_testingDirectory.clear()
            self.dlg.pushButton_testingDirectory.clicked.connect(self.select_testing_directory)

            self.dlg.finished.connect(self.result)

            self.dlg.lineEdit_trainingDirectory.setText("C:/Users/Carolina/Documents/Tesis/Tiff Files/HighLevel/Training2")

        self.dlg.open()


    def result(self, result):
        if result:
            features = []
            if self.dlg.checkBox_bandsAlgebra.isChecked():
                features.append(AlgebraFeature())
            if self.dlg.checkBox_medianFilter.isChecked():
                features.append(FilterFeature())
                features.append(FilterGaussFeature())
            if self.dlg.checkBox_ndvi.isChecked():
                features.append(NdviFeature())
            if self.dlg.checkBox_dem.isChecked():
                features.append(DayFeature())
            # if self.dlg.checkBox_textures.isChecked():
            #     features.append(TextureFeature())

            self.train_task = TrainTask(
                training_directory = self.dlg.lineEdit_trainingDirectory.text(),
                features = features,

                do_testing = self.dlg.checkBox_testing.isChecked(),
                testing_directory = self.dlg.lineEdit_testingDirectory.text(),

                do_prediction = self.dlg.checkBox_prediction.isChecked(),
                prediction_directory = self.dlg.lineEdit_predictionDirectoy.text(),
                lumberjack_instance = self
                )

            QgsApplication.taskManager().addTask(self.train_task)


    def notify_training(self, start_time, classes_training, total_samples, time):
        self.dlg.plainTextEdit.appendPlainText("======== {} ========".format(str(start_time)))
        self.dlg.plainTextEdit.appendPlainText("Classes when training:")
        for i in classes_training:
            self.dlg.plainTextEdit.appendPlainText("- " + str(i))
        self.dlg.plainTextEdit.appendPlainText("Total samples: {}".format(str(total_samples)))
        self.dlg.plainTextEdit.appendPlainText("Finished in {} seconds".format(str(time)))
        self.dlg.plainTextEdit.appendPlainText("")

        self.dlg.open()


    def notify_metrics(self, start_time, classes_training, classes_output, metrics, time):
        self.dlg.plainTextEdit.appendPlainText("======== {} ========".format(str(start_time)))
        self.dlg.plainTextEdit.appendPlainText("Classes when training:")
        for i in classes_training:
            self.dlg.plainTextEdit.appendPlainText("- " + str(i))
        if classes_output is not None:
            self.dlg.plainTextEdit.appendPlainText("Classes when testing:")
            for i in classes_output:
                self.dlg.plainTextEdit.appendPlainText("- " + str(i))

        if metrics is not None:
            for i in metrics[:-1]:
                self.dlg.plainTextEdit.appendPlainText(str(i))
            self.dlg.plainTextEdit.appendPlainText("Finished in {} seconds".format(str(time)))
            self.dlg.plainTextEdit.appendPlainText("")

        self.dlg.open()

        # Barchart window with feature importances
        self.plotWindow = PlotWindow(self.dlg, feature_importances=metrics[-1])
        self.plotWindow.show()

    def notify_task(self, start_time, output_files):
        if self.dlg.checkBox_prediction.isChecked():
            self.iface.messageBar().pushMessage("Success", "Output file/s created", level=Qgis.Success, duration=5)
            if self.dlg.checkBox_addFile.isChecked():
                for file_path in output_files:
                    file_name = file_path.split("/")[-1]
                    self.iface.addRasterLayer(file_path, file_name)
                    layers = QgsProject.instance().mapLayersByName(file_name)
                    abs_style_path = self.plugin_dir + "/prediction_tree_style.qml"
                    layers[0].loadNamedStyle(abs_style_path)
                    self.iface.layerTreeView().refreshLayerSymbology(layers[0].id())
