from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QMessageBox, QVBoxLayout, QCheckBox, QButtonGroup
from PyQt5 import uic
from helper import res_path, classlistToIds
from PyQt5.QtCore import QTimer
import main
from base_ui import WidgetUI

# for graph here, need pyqtgraph and numpy
from pyqtgraph import PlotWidget, PlotItem, plot
import pyqtgraph as pg


class EffectPlot():
    MAX_DATAPOINTS = 1000

    EFFECT_NAME_LOOKUP = {
        0x00: 'None',
        0x01: 'Constant Force',
        0x02: 'Ramp',
        0x03: 'Square',
        0x04: 'Sine',
        0x05: 'Triangle',
        0x06: 'SawtoothUp',
        0x07: 'SawtoothDown',
        0x08: 'Spring',
        0x09: 'Damper',
        0x0A: 'Inertia',
        0x0B: 'Friction',
        0x0C: 'Custom',
    }

    def __init__(self, widget, log, color='y', custom_effect=None):
        self.widget = widget
        self.plot = widget.plot(pen=color)  # type: PlotItem
        self.last_effect = None
        self.log = log
        self.custom_effect = custom_effect

        if custom_effect:
            self._setTitle(custom_effect)

        self._clearData()

    def updateData(self, report_string):
        if self.custom_effect and self.data == []:
            self._setTitle(self.custom_effect)

        try:
            if self.custom_effect:
                self._addData(float(report_string))
            else:
                effect_index, value = report_string.split(',')
                effect_index = int(effect_index)
                if effect_index != self.last_effect:
                    self.last_effect = effect_index
                    self._clearData()
                    self._setTitle(self.EFFECT_NAME_LOOKUP[effect_index])

                self._addData(float(value))
        except Exception as e:
            self.log("Plot Update error: " + str(e))

    def disable(self):
        self._setTitle(None)
        self.data = []
        self._updatePlot()
        self.last_effect = None  

    def _setTitle(self, title):
        self.widget.setTitle(title)

    def _clearData(self):
        self.data = [0] * self.MAX_DATAPOINTS
        self._updatePlot()

    def _addData(self, value):
        value = float(value)
        self.data = self.data[max(len(self.data)-self.MAX_DATAPOINTS, 0):]
        self.data.append(value)
        self._updatePlot()

    def _updatePlot(self):
        self.plot.setData(self.data)


class EffectPlotterUI(WidgetUI):
    def __init__(self, main=None):
        super().__init__(ui_form='effect_plotter.ui')
        self.main = main  # type: main.MainUi

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateTimer)      
        
        self.totalPlot = EffectPlot(self.graphWidget_1, main.log, custom_effect='Total')

        self.plots = [
            EffectPlot(self.graphWidget_2, main.log),
            EffectPlot(self.graphWidget_3, main.log),
            EffectPlot(self.graphWidget_4, main.log),
            EffectPlot(self.graphWidget_5, main.log),
            EffectPlot(self.graphWidget_6, main.log),
            EffectPlot(self.graphWidget_7, main.log),
            EffectPlot(self.graphWidget_8, main.log),
        ]

    def showEvent(self, event):
        self.timer.start(50)
    
    def hideEvent(self, event):
        self.timer.stop()

    def updateTimer(self):
        self.main.comms.serialGetAsync('effreport', self.handleEffectReport)

    def handleEffectReport(self, report):
        total_torque, effect_reports = report.strip().split(':')
        effect_reports = [s for s in effect_reports.split(';') if s.strip() != '']

        self.totalPlot.updateData(total_torque)

        plots_used = 0
        for i in range(min(len(self.plots), len(effect_reports))):
            self.plots[i].updateData(effect_reports[i])
            plots_used += 1
        
        for i in range(plots_used, len(self.plots)):
            self.plots[i].disable()
            