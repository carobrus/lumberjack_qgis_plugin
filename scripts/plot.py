from PyQt5.QtWidgets import QApplication, QMainWindow, QMenu, QVBoxLayout
from PyQt5.QtWidgets import QSizePolicy, QMessageBox, QWidget
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas)
from matplotlib.figure import Figure
import matplotlib.pyplot as plt


class PlotWindow(QMainWindow):
    def __init__(self, parent=None, feature_importances=None):
        super(PlotWindow, self).__init__(parent)
        self.title = 'Feature Importances'
        self.width = 640
        self.height = 480
        self.feature_importances = feature_importances
        self.initUI()


    def initUI(self):
        self.setWindowTitle(self.title)
        # self.resize(self.width, self.height)
        self.setFixedSize(self.width, self.height)
        m = PlotCanvas(self, feature_importances=self.feature_importances)
        m.move(0,0)
        self.show()


class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None, dpi=100, feature_importances=None):
        fig = Figure(dpi=dpi)
        fig.tight_layout()
        self.axes = fig.add_subplot(111)
        self.feature_importances = feature_importances
        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(
            self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        self.plot()


    def plot(self):
        data = self.feature_importances
        y = list(range(1, len(data)+1))
        ax = self.figure.add_subplot(111)
        ax.bar(y, data)
        ax.set_title('Features Importance')
        self.draw()
