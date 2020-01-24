from PyQt5.QtWidgets import QApplication, QMainWindow, QMenu, QVBoxLayout
from PyQt5.QtWidgets import QSizePolicy, QMessageBox, QWidget
from PyQt5 import QtGui
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas)
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np


class PlotWindow(QMainWindow):
    def __init__(self, parent=None, feature_importances=None, labels=None):
        super(PlotWindow, self).__init__(parent)
        self.title = 'Feature Importances'
        self.width = 640
        self.height = 700
        self.feature_importances = feature_importances
        self.labels = labels
        self.initUI()


    def initUI(self):
        self.setWindowTitle(self.title)
        self.resize(self.width, self.height)
        # self.setFixedSize(self.width, self.height)
        layout = QtGui.QVBoxLayout()
        self.plot_canvas = PlotCanvas(self,
            feature_importances=self.feature_importances,
            labels=self.labels)
        layout.addWidget(self.plot_canvas)
        # m.move(0,0)
        self.setLayout(layout)
        # self.show()


class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None, dpi=100, feature_importances=None,
                 labels=None):
        super(PlotCanvas, self).__init__(Figure())
        self.setParent(parent)
        fig = Figure(dpi=dpi)
        self.canvas = FigureCanvas(self.figure)
        # fig.tight_layout()
        # fig.set_size_inches(5, 7, forward=True)
        self.axes = fig.add_subplot(111)
        self.feature_importances = feature_importances
        self.labels = labels

        FigureCanvas.setSizePolicy(
            self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        self.plot()


    def plot(self):
        data = self.feature_importances
        y = self.labels
        y_pos = np.arange(len(self.labels))

        ax = self.figure.add_subplot(111)
        ax.barh(y_pos, data, align='center')
        ax.set_yticks(y_pos)
        ax.set_yticklabels(y)
        ax.invert_yaxis()
        ax.set_title('Features Importance')
        self.draw()
