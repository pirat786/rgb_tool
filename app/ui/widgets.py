from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath
from PyQt6.QtCore import Qt
import numpy as np

class HistogramWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        self.hist_data = None # {'r': [], 'g': [], 'b': []}

    def set_data(self, r_hist, g_hist, b_hist):
        self.hist_data = {'r': r_hist, 'g': g_hist, 'b': b_hist}
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        # Background
        painter.fillRect(0, 0, w, h, QColor("#1e1e1e"))
        painter.setPen(QPen(QColor("#444"), 1))
        painter.drawRect(0, 0, w-1, h-1)

        if not self.hist_data or len(self.hist_data['r']) == 0:
            painter.setPen(QColor("#777"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Нет данных для гистограммы")
            return

        # Draw histograms
        # Max value for normalization
        max_val = max(
            np.max(self.hist_data['r']), 
            np.max(self.hist_data['g']), 
            np.max(self.hist_data['b'])
        )
        
        if max_val == 0: return

        self.draw_channel(painter, self.hist_data['r'], QColor(255, 50, 50, 150), w, h, max_val)
        self.draw_channel(painter, self.hist_data['g'], QColor(50, 255, 50, 150), w, h, max_val)
        self.draw_channel(painter, self.hist_data['b'], QColor(50, 50, 255, 150), w, h, max_val)

    def draw_channel(self, painter, data, color, w, h, max_val):
        path = QPainterPath()
        path.moveTo(0, h)
        
        bin_w = w / 256
        
        for i, val in enumerate(data):
            bar_h = (val / max_val) * (h - 10) # 10px padding top
            x = i * bin_w
            y = h - bar_h
            path.lineTo(x, y)
            path.lineTo(x + bin_w, y)
            
        path.lineTo(w, h)
        path.closeSubpath()
        
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)

class LineProfileWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        self.profile_data = None # {'r': [], 'g': [], 'b': []}

    def set_data(self, r, g, b):
        self.profile_data = {'r': r, 'g': g, 'b': b}
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        # Background
        painter.fillRect(0, 0, w, h, QColor("#1e1e1e"))
        painter.setPen(QPen(QColor("#444"), 1))
        painter.drawRect(0, 0, w-1, h-1)

        if not self.profile_data or len(self.profile_data['r']) == 0:
            painter.setPen(QColor("#777"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Нарисуйте линию для профиля")
            return

        # Max value is usually 255 for images
        max_val = 255
        
        # Draw grid lines for 0, 128, 255
        painter.setPen(QPen(QColor("#333"), 1, Qt.PenStyle.DashLine))
        painter.drawLine(0, h//2, w, h//2)
        
        num_points = len(self.profile_data['r'])
        step_x = w / (num_points - 1) if num_points > 1 else w

        self.draw_line(painter, self.profile_data['r'], QColor(255, 50, 50), w, h, max_val, step_x)
        self.draw_line(painter, self.profile_data['g'], QColor(50, 255, 50), w, h, max_val, step_x)
        self.draw_line(painter, self.profile_data['b'], QColor(50, 50, 255), w, h, max_val, step_x)

    def draw_line(self, painter, data, color, w, h, max_val, step_x):
        path = QPainterPath()
        
        # Start point
        y_start = h - (data[0] / max_val) * (h - 10)
        path.moveTo(0, y_start)
        
        for i, val in enumerate(data):
            if i == 0: continue
            y = h - (val / max_val) * (h - 10)
            x = i * step_x
            path.lineTo(x, y)
            
        pen = QPen(color, 2)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
