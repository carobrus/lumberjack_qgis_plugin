from PyQt5.QtWidgets import QApplication, QMainWindow, QMenu, QVBoxLayout, QSizePolicy, QMessageBox, QWidget
from PyQt5 import QtGui
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np


class PlotWindow(QMainWindow):
    def __init__(self, parent=None, data=None, days=None):
        super(PlotWindow, self).__init__(parent)
        self.title = 'Thresholds'
        self.width = 800
        self.height = 700
        self.data = data
        self.days = days
        self.initUI()


    def initUI(self):
        self.setWindowTitle(self.title)
        self.setMinimumSize(500, 500)
        self.resize(self.width, self.height)

        layout = QtGui.QVBoxLayout()
        self.plot_canvas = PlotCanvas(self, data=self.data, days=self.days)
        layout.addWidget(self.plot_canvas)
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        self.show()


class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None, dpi=100, data=None, days=None):
        self.fig = Figure(dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.data = data
        self.days = days
        # FigureCanvas.updateGeometry(self)
        self.plot()
        self.fig.tight_layout()


    def plot(self):
        data = self.data
        if (self.days != []):
            self.axes.set_xticklabels(self.days, rotation=90)
            self.axes.boxplot(data, showfliers=False, positions=self.days, widths=3)
            self.axes.set_xlim(xmin=0, xmax=366)
        self.axes.set_title('Threshholds')
        self.draw()
