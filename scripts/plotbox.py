from PyQt5.QtWidgets import QApplication, QMainWindow, QMenu, QVBoxLayout
from PyQt5.QtWidgets import QSizePolicy, QMessageBox, QWidget
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas)
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np


class PlotWindow(QMainWindow):
    def __init__(self, parent=None, data=None, days=None):
        super(PlotWindow, self).__init__(parent)
        self.title = 'Thresholds'
        self.width = 1000
        self.height = 700
        self.data = data
        self.days = days
        self.initUI()


    def initUI(self):
        self.setWindowTitle(self.title)
        self.resize(self.width, self.height)
        # self.setFixedSize(self.width, self.height)
        m = PlotCanvas(self, data=self.data, days=self.days)
        m.move(0,0)
        layout = QVBoxLayout()
        layout.addWidget(m)
        self.show()


class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None, dpi=100, data=None, days=None):
        fig = Figure(dpi=dpi)
        fig.tight_layout()
        fig.set_size_inches(10,7,forward=True)
        self.axes = fig.add_subplot(111)
        self.data = data
        self.days = days
        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(
            self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        self.plot()


    def plot(self):
        data = self.data
        ax = self.figure.add_subplot(111)
        if (self.days != []):
            ax.set_xticklabels(self.days, rotation=90)
            ax.boxplot(data, showfliers=False, positions=self.days, widths=3)
            ax.set_xlim(xmin=0, xmax=366)
        # ax.set_title('Threshholds')
        self.draw()
