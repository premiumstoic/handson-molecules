"""Status card widgets from Ali's T4 design. What to show is decided in status.py."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from .gestures import HandShape
from .status import GESTURE_VIEWS, INK, STYLES, CardView

ASSETS = Path(__file__).resolve().parent / "assets"


class StatusCard(QFrame):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        self.title = QLabel()
        self.icon = QLabel()
        self.icon.setFixedHeight(130)
        self.label = QLabel()
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.progress = QProgressBar()  # open palm hold-to-reset
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(10)
        policy = self.progress.sizePolicy()
        policy.setRetainSizeWhenHidden(True)  # showing the bar must not resize the card
        self.progress.setSizePolicy(policy)
        for widget in (self.title, self.icon, self.label, self.hint):
            widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(widget)
        layout.addWidget(self.progress)
        self._icon_effect = QGraphicsOpacityEffect(self.icon)
        self.icon.setGraphicsEffect(self._icon_effect)
        self._pixmaps: dict[str, QPixmap] = {}
        self._view: CardView | None = None
        self.set_progress(0)

    def show_view(self, view: CardView) -> None:
        if view == self._view:
            return
        self._view = view
        background, border = STYLES[view.style]
        self.setStyleSheet(f"""
            #card {{ background: {background}; border: 5px solid {border}; border-radius: 22px; }}
            #card QLabel {{ color: {INK}; background: transparent; }}
            #card QProgressBar {{ background: #ffffff; border: none; border-radius: 5px; }}
            #card QProgressBar::chunk {{ background: {border}; border-radius: 5px; }}
        """)
        self.title.setText(f"<span style='font-size:16px; font-weight:700'>{view.title}</span>")
        self.title.setVisible(bool(view.title))
        self.icon.setPixmap(self._pixmap(view.icon))
        self._icon_effect.setOpacity(0.35 if view.faded else 1.0)
        self.label.setText(f"<span style='font-size:24px; font-weight:800'>{view.label}</span>")
        self.hint.setText(f"<span style='font-size:13px; font-weight:600'>{view.hint}</span>")

    def set_progress(self, fraction: float) -> None:
        self.progress.setValue(round(fraction * 100))
        self.progress.setVisible(fraction > 0)

    def _pixmap(self, name: str) -> QPixmap:
        if name not in self._pixmaps:
            self._pixmaps[name] = QPixmap(str(ASSETS / name)).scaledToHeight(
                120, Qt.TransformationMode.SmoothTransformation)
        return self._pixmaps[name]


class GestureLegend(QWidget):
    """Small icons for the three gestures; the active one is highlighted."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(72)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._items: dict[HandShape, tuple[QLabel, QGraphicsOpacityEffect]] = {}
        for shape, (icon, label, _hint) in GESTURE_VIEWS.items():
            item = QLabel()
            item.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pixmap = QPixmap(str(ASSETS / icon)).scaledToHeight(40, Qt.TransformationMode.SmoothTransformation)
            item.setPixmap(pixmap)
            item.setToolTip(label)
            # Mini cards as in Ali's mockup; the inactive ones are faded as a whole.
            item.setStyleSheet(f"background: {STYLES['active'][0]}; border: 3px solid {STYLES['active'][1]};"
                               " border-radius: 12px; padding: 4px;")
            effect = QGraphicsOpacityEffect(item)
            item.setGraphicsEffect(effect)
            layout.addWidget(item)
            self._items[shape] = (item, effect)
        self.highlight(HandShape.NONE)

    def highlight(self, shape: HandShape) -> None:
        for item_shape, (_item, effect) in self._items.items():
            effect.setOpacity(1.0 if item_shape is shape else 0.35)
