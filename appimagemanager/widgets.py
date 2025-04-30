from PyQt6.QtWidgets import QCheckBox
from PyQt6.QtCore import pyqtProperty, QPropertyAnimation, QEasingCurve, Qt, QSize
from PyQt6.QtGui import QPainter, QColor, QFont
from PyQt6.QtCore import QRect

class ToggleSwitch(QCheckBox):
    """A toggle switch with sliding circle and sun/moon icons."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._circle_position = 2
        # Animation for sliding circle
        self._animation = QPropertyAnimation(self, b"circle_position", self)
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.toggled.connect(self._start_animation)
        # Ensure initial position
        self._start_animation()

    def _start_animation(self):
        start = self._circle_position
        end = self.width() - self.height() + 2 if self.isChecked() else 2
        self._animation.stop()
        self._animation.setStartValue(start)
        self._animation.setEndValue(end)
        self._animation.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Draw background
        bg_color = QColor("#007AFF") if self.isChecked() else QColor("#ccc")
        painter.setBrush(bg_color)
        painter.setPen(Qt.PenStyle.NoPen)
        rect = self.rect()
        painter.drawRoundedRect(rect, rect.height()/2, rect.height()/2)
        # Draw sliding circle
        diameter = rect.height() - 4
        circle_rect = QRect(self._circle_position, 2, diameter, diameter)
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(circle_rect)
        # Draw icon
        painter.setPen(QColor("#007AFF") if self.isChecked() else QColor("#666"))
        font = QFont()
        font.setPointSize(int(diameter * 0.55))
        painter.setFont(font)
        symbol = "☾" if self.isChecked() else "☀"
        painter.drawText(circle_rect, Qt.AlignmentFlag.AlignCenter, symbol)
        painter.end()

    def get_circle_position(self):
        return self._circle_position

    def set_circle_position(self, pos):
        self._circle_position = pos
        self.update()

    circle_position = pyqtProperty(int, get_circle_position, set_circle_position)

    def sizeHint(self):
        """Provide a suitable size for the toggle switch for proper rendering."""
        return QSize(50, 24)

    def hitButton(self, pos):
        # Ensure clicks anywhere in the widget toggle the switch
        return True 