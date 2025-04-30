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
        # Set initial position based on default checked state (usually False)
        self._circle_position = 2 # Initial position for unchecked state
        # Animation for sliding circle
        self._animation = QPropertyAnimation(self, b"circle_position", self)
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        # Connect signal AFTER initial state might be set
        self.toggled.connect(self._start_animation)
        # DO NOT CALL _start_animation() here initially

    def _start_animation(self):
        # Always calculate end based on the CURRENT checked state
        end = self.width() - self.height() + 2 if self.isChecked() else 2
        start = self._circle_position # Start from current visual position

        # If the animation is already running for the *same* target, don't restart
        # (This might prevent issues if setChecked triggers toggled signal internally)
        if self._animation.state() == QPropertyAnimation.State.Running and self._animation.endValue() == end:
             return

        self._animation.stop()
        self._animation.setStartValue(start)
        self._animation.setEndValue(end)
        self._animation.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Get dimensions (ensure height > 4 for calculations)
        rect = self.rect()
        h = max(rect.height(), 5) # Use at least 5 to avoid division by zero or negative radius
        w = rect.width()
        diameter = h - 4
        radius = diameter / 2.0
        
        # Draw background
        bg_color = QColor("#007AFF") if self.isChecked() else QColor("#ccc")
        painter.setBrush(bg_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, h / 2, h / 2)
        
        # Draw sliding circle
        # Ensure circle position is valid given current width
        # Clamp position to be within bounds [2, w - h + 2]
        max_pos = w - h + 2
        current_pos = max(2, min(self._circle_position, max_pos)) 
        circle_rect = QRect(int(current_pos), 2, diameter, diameter)
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(circle_rect)
        
        # Draw icon if diameter is large enough
        if diameter > 5:
             painter.setPen(QColor("#007AFF") if self.isChecked() else QColor("#666"))
             font = QFont()
             font.setPointSize(int(diameter * 0.55))
             painter.setFont(font)
             symbol = "☾" if self.isChecked() else "☀"
             painter.drawText(circle_rect, Qt.AlignmentFlag.AlignCenter, symbol)
             
        painter.end()

    # Add resizeEvent to correctly set initial position
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Update circle position *without* animation when resized/first shown,
        # based on the current logical state.
        # Use the final width/height from the event or self.
        end_pos = self.width() - self.height() + 2 if self.isChecked() else 2
        # Only update if the position calculation is valid (width >= height)
        if self.width() >= self.height():
            self._circle_position = end_pos
            # No need to call self.update() here, resizeEvent implies a repaint
        
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