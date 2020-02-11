from PyQt5.QtWidgets import QApplication, QMainWindow, QMenu, QSizePolicy, QGridLayout
from PyQt5.QtWidgets import QMessageBox, QWidget, QPushButton
from PyQt5 import QtGui, QtCore
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np


class PlotWindow(QMainWindow):
    def __init__(self, parent=None, feature_importances=None, labels=None):
        super(PlotWindow, self).__init__(parent)
        self.title = 'Feature Importances'
        self.width = 640
        self.height = 930
        self.feature_importances = feature_importances
        self.labels = labels
        self.initUI()


    def initUI(self):
        self.setWindowTitle(self.title)
        self.setMinimumSize(500, 500)
        self.resize(self.width, self.height)
        # main_layout = QtGui.QVBoxLayout()
        self.plot_canvas = PlotCanvas(self, feature_importances=self.feature_importances, labels=self.labels)
        
        self.button = QPushButton("")
        self.button.setIcon(QtGui.QIcon(':/plugins/Lumberjack/sort.png'))
        self.button.setIconSize(QtCore.QSize(40,40))
        self.button.setFixedSize(QtCore.QSize(40,40))

        self.button.clicked.connect(self.plot_canvas.plot)       

        # main_layout.addWidget(self.plot_canvas)
        # main_layout.addWidget(self.button, alignment=QtCore.Qt.AlignRight)
        # widget = QWidget()
        # widget.setLayout(main_layout)
        # self.setCentralWidget(widget)

        main_layout = QGridLayout()
        main_layout.addWidget(self.plot_canvas, 0, 0, 1, 1)
        main_layout.addWidget(self.button, 0, 0, 1, 1, QtCore.Qt.AlignRight | QtCore.Qt.AlignTop)
        widget = QWidget()
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)

        self.show()
    

class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None, dpi=100, feature_importances=None, labels=None):
        self.fig = Figure(dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.fig.subplots_adjust(left=0.2, bottom=0.05, right=0.99, top=0.95, wspace=0, hspace=0)
        self.feature_importances = feature_importances
        self.labels = labels
        # FigureCanvas.updateGeometry(self)
        self.sorted = False
        self.plot()
        self.fig.tight_layout()


    def plot(self):
        data = self.feature_importances
        y = self.labels
        y_pos = np.arange(len(self.labels))
        
        if (self.sorted):
            data, y = (list(t) for t in zip(*sorted(zip(data, y), reverse=True)))
        self.sorted = not self.sorted

        self.axes.clear()
        self.axes.barh(y_pos, data, align='center')
        self.axes.set_yticks(y_pos)
        self.axes.set_yticklabels(y)
        self.axes.invert_yaxis()
        self.axes.set_title('Features Importance')
        self.draw()

