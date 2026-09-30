"""Main window: 3D molecule view, webcam preview and status panel."""

import os

os.environ.setdefault("QT_API", "pyside6")  # make pyvistaqt use PySide6

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMainWindow, QVBoxLayout, QWidget
from pyvistaqt import QtInteractor

from . import molecule
from .controller import ViewController
from .gestures import HandShape, classify
from .logger import EventLogger
from .tracking import HandTracker

PREVIEW_SIZE = (320, 240)
TRACKING_LOST_AFTER_S = 0.5
KEY_ROTATE_DEG = 10
KEY_ZOOM = 1.15


class MainWindow(QMainWindow):
    def __init__(self, molecule_name: str, model_path: Path, camera_index: int, log_dir: Path):
        super().__init__()
        self.setWindowTitle(f"HandsOn Molecules - {molecule_name}")
        self.resize(1200, 720)

        self.plotter = QtInteractor(self)
        self.plotter.set_background("#101a24")
        molecule.add_to_plotter(self.plotter, molecule.load(molecule_name))
        self.controller = ViewController(self.plotter)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addWidget(self.plotter.interactor, stretch=3)
        layout.addWidget(self._build_side_panel(), stretch=1)
        self.setCentralWidget(central)
        self._add_shortcuts()

        self.logger = EventLogger(log_dir)
        self.logger.log("app_start", molecule_name)

        self.tracker: HandTracker | None = HandTracker(model_path, camera_index)
        try:
            self.tracker.start()
            self._set_status(self.tracking_label, "Waiting for hand", "neutral")
        except (FileNotFoundError, RuntimeError) as error:
            self.tracker = None
            self._set_status(self.tracking_label, "Camera off", "bad")
            self.preview.setText(str(error))
            self.logger.log("tracking_unavailable", str(error))

        self._last_frame_time: float | None = None
        self._last_hand_time: float | None = None
        self._hand_visible = False
        self._last_shape = HandShape.NONE
        self._last_action = ""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(33)  # ~30 updates per second

    def _build_side_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("side")
        layout = QVBoxLayout(panel)

        self.preview = QLabel("Starting camera...")
        self.preview.setFixedSize(*PREVIEW_SIZE)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setWordWrap(True)
        self.preview.setObjectName("preview")
        layout.addWidget(self.preview)

        self.tracking_label = QLabel()
        self.shape_label = QLabel("Gesture: -")
        self.action_label = QLabel("Action: -")
        self.fps_label = QLabel("Camera: - fps")
        for label in (self.tracking_label, self.shape_label, self.action_label, self.fps_label):
            layout.addWidget(label)

        help_text = QLabel(
            "<b>Gestures</b><br>Fist + move: rotate<br>Pinch + spread/close: zoom<br>Open palm (hold 1 s): reset"
            "<br><br><b>Keyboard (testing)</b><br>Arrow keys: rotate<br>+ / -: zoom<br>R: reset")
        help_text.setObjectName("help")
        layout.addWidget(help_text)
        layout.addStretch()

        panel.setStyleSheet("""
            #side { background: #18232e; border-radius: 8px; }
            #side QLabel { color: #dde6ee; font-size: 14px; }
            #preview { background: #0b1117; border-radius: 6px; color: #9fb0bf; }
            #help { color: #9fb0bf; font-size: 12px; }
        """)
        return panel

    def _add_shortcuts(self) -> None:
        bindings = {
            Qt.Key.Key_Left: lambda: self.controller.rotate(-KEY_ROTATE_DEG, 0),
            Qt.Key.Key_Right: lambda: self.controller.rotate(KEY_ROTATE_DEG, 0),
            Qt.Key.Key_Up: lambda: self.controller.rotate(0, KEY_ROTATE_DEG),
            Qt.Key.Key_Down: lambda: self.controller.rotate(0, -KEY_ROTATE_DEG),
            Qt.Key.Key_Plus: lambda: self.controller.zoom(KEY_ZOOM),
            Qt.Key.Key_Equal: lambda: self.controller.zoom(KEY_ZOOM),
            Qt.Key.Key_Minus: lambda: self.controller.zoom(1 / KEY_ZOOM),
            Qt.Key.Key_R: self.controller.reset,
        }
        for key, action in bindings.items():
            QShortcut(QKeySequence(key), self, activated=action)

    def _tick(self) -> None:
        if self.tracker is None:
            return
        frame = self.tracker.latest()
        if frame is None or frame.timestamp == self._last_frame_time:
            return
        self._last_frame_time = frame.timestamp
        self._show_preview(frame.image)
        self.fps_label.setText(f"Camera: {frame.fps:.0f} fps")

        if frame.landmarks is not None:
            self._last_hand_time = frame.timestamp
            if not self._hand_visible:
                self._hand_visible = True
                self.logger.log("hand_detected", frame.handedness or "")
            self._set_status(self.tracking_label, f"Hand detected ({frame.handedness})", "good")
        elif self._hand_visible and frame.timestamp - self._last_hand_time > TRACKING_LOST_AFTER_S:
            self._hand_visible = False
            self.logger.log("tracking_lost")
        if not self._hand_visible and self._last_hand_time is not None:
            self._set_status(self.tracking_label, "Tracking lost - show your hand", "bad")

        shape = classify(frame.landmarks)
        if shape != self._last_shape:
            self.logger.log("gesture", shape.value)
            self._last_shape = shape
        self.shape_label.setText(f"Gesture: {shape.value}")

        action = self.controller.update(shape, frame.landmarks)
        if action != self._last_action:
            self.logger.log("action", action)
            self._last_action = action
        self.action_label.setText(f"Action: {action}")

    def _show_preview(self, rgb) -> None:
        height, width, _ = rgb.shape
        image = QImage(rgb.data, width, height, 3 * width, QImage.Format.Format_RGB888).copy()
        self.preview.setPixmap(QPixmap.fromImage(image).scaled(
            *PREVIEW_SIZE, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    @staticmethod
    def _set_status(label: QLabel, text: str, level: str) -> None:
        color = {"good": "#64cdb9", "bad": "#ff7a7a", "neutral": "#dde6ee"}[level]
        label.setText(f"<span style='color:{color}'>&#9679;</span> {text}")

    def closeEvent(self, event) -> None:
        self.timer.stop()
        if self.tracker:
            self.tracker.stop()
        self.logger.log("app_exit")
        self.logger.close()
        self.plotter.close()
        super().closeEvent(event)
