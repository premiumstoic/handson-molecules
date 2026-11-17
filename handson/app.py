"""Main window: 3D molecule view, webcam preview and status panel."""

import os

os.environ.setdefault("QT_API", "pyside6")  # make pyvistaqt use PySide6

from pathlib import Path

import numpy as np

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (QComboBox, QFrame, QHBoxLayout, QLabel, QMainWindow, QStackedWidget, QVBoxLayout,
                               QWidget)
from pyvistaqt import QtInteractor

from . import molecule
from .controller import ViewController
from .filters import OneEuroFilter
from .goals import CameraView
from .gestures import GestureFilter, HandShape
from .logger import EventLogger
from .status import card_view
from .status_panel import GestureLegend, StatusCard
from .study import StudySession
from .tracking import HandTracker

PREVIEW_SIZE = (320, 240)
TRACKING_LOST_AFTER_S = 0.5
KEY_ROTATE_DEG = 10
KEY_ZOOM = 1.15


class MainWindow(QMainWindow):
    def __init__(self, molecule_name: str, model_path: Path, camera_index: int, log_dir: Path,
                 participant: str | None = None, condition: str = "gesture"):
        super().__init__()
        self.resize(1200, 760)
        self.logger = EventLogger(log_dir, tag=f"{participant}-{condition}" if participant else "")
        self.logger.log("app_start", molecule_name)
        self.study = StudySession(self.logger, participant, condition) if participant else None

        self.plotter = QtInteractor(self)
        self.plotter.set_background("#101a24")
        self.controller = ViewController(self.plotter)

        # In study mode the 3D view swaps with a message page for the intro and the results.
        # A page in a stack, not a widget on top: the VTK view draws over any widget laid over it.
        self.message = QLabel()
        self.message.setObjectName("message")
        self.message.setWordWrap(True)
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message.setStyleSheet("""
            QLabel#message { background: #101a24; color: #dde6ee; font-size: 18px; padding: 60px; }
        """)
        self.view_stack = QStackedWidget()
        self.view_stack.addWidget(self.plotter.interactor)
        self.view_stack.addWidget(self.message)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addWidget(self.view_stack, stretch=3)
        layout.addWidget(self._build_side_panel(), stretch=1)
        self.setCentralWidget(central)
        self._add_shortcuts()
        if self.study:
            self._show_study()
            self.study_label.setVisible(True)
            self.task_label.setVisible(True)
        self.show_molecule(molecule_name)

        self.tracker: HandTracker | None = None
        self._tracking = "waiting"  # "mouse", "off", "waiting", "detected" or "lost"
        if self.study and self.study.condition == "mouse":
            self._tracking = "mouse"
            self.preview.setText("Mouse condition: camera off")
        else:
            if self.study:
                self.plotter.disable()  # gesture condition: the mouse must not move the molecule
            self.tracker = HandTracker(model_path, camera_index)
            try:
                self.tracker.start()
            except (FileNotFoundError, RuntimeError) as error:
                self.tracker = None
                self._tracking = "off"
                self.preview.setText(str(error))
                self.logger.log("tracking_unavailable", str(error))
        self.card.show_view(card_view(self._tracking, HandShape.NONE))

        self._last_frame_time: float | None = None
        self._last_hand_time: float | None = None
        self.landmark_filter = OneEuroFilter()
        self.gestures = GestureFilter()
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

        self.study_label = QLabel()
        self.study_label.setObjectName("study")
        self.study_label.setVisible(False)
        layout.addWidget(self.study_label)
        self.task_label = QLabel()  # what the participant has to do
        self.task_label.setObjectName("task")
        self.task_label.setWordWrap(True)
        self.task_label.setVisible(False)
        layout.addWidget(self.task_label)
        self.card = StatusCard()
        layout.addWidget(self.card)
        self.legend = GestureLegend()
        layout.addWidget(self.legend)

        self.molecule_box = QComboBox()
        self.molecule_box.addItems([name.capitalize() for name in molecule.MOLECULES])
        self.molecule_box.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # keep arrow keys for rotating
        self.molecule_box.activated.connect(lambda i: self.show_molecule(list(molecule.MOLECULES)[i]))
        layout.addWidget(self.molecule_box)

        help_text = QLabel(
            "<b>Gestures</b><br>Fist + move: rotate<br>Pinch + move up/down: zoom<br>Open palm (hold 1 s): reset"
            "<br><br><b>Keyboard (testing)</b><br>Arrow keys: rotate<br>+ / -: zoom<br>R: reset"
            "<br>N / P: next / previous molecule")
        help_text.setObjectName("help")
        layout.addWidget(help_text)
        layout.addStretch()
        self.fps_label = QLabel("Camera: - fps")
        self.fps_label.setObjectName("help")
        layout.addWidget(self.fps_label)

        panel.setStyleSheet("""
            #side { background: #18232e; border-radius: 8px; }
            #side > QLabel { color: #dde6ee; font-size: 14px; }
            #preview { background: #0b1117; border-radius: 6px; color: #9fb0bf; }
            #help { color: #9fb0bf; font-size: 12px; }
            QLabel#study { color: #101a24; background: #f0cd6c; border-radius: 6px; padding: 6px;
                     font-size: 13px; font-weight: 700; }
            QLabel#task { color: #ffffff; background: #2b3a48; border: 2px solid #f0cd6c; border-radius: 8px;
                    padding: 10px; font-size: 17px; font-weight: 600; }
            QComboBox { font-size: 14px; padding: 4px; }
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
            Qt.Key.Key_N: lambda: self._step_molecule(1),
            Qt.Key.Key_P: lambda: self._step_molecule(-1),
        }
        if self.study:
            bindings.update({
                Qt.Key.Key_T: self._start_task,
                Qt.Key.Key_Space: self.study.skip_task,
                Qt.Key.Key_F: self.study.false_trigger,
            })
        for key, action in bindings.items():
            QShortcut(QKeySequence(key), self, activated=lambda action=action: self._run(action))

    def _run(self, action) -> None:
        action()
        if self.study:
            self._show_study()

    def _start_task(self) -> None:
        task = self.study.start_task()
        if task:
            self.show_molecule(task.molecule)  # also resets the view, so every task starts the same

    def _check_task(self) -> None:
        camera = self.plotter.camera
        view = CameraView(np.array(camera.position), np.array(camera.focal_point), camera.view_angle)
        was_met = self.study.goal_met
        outcome = self.study.update(self.study.current.goal.met(self.molecule, view))
        if outcome or self.study.goal_met != was_met:
            self._show_study()

    def _show_study(self) -> None:
        self.study_label.setText(self.study.status_text())
        self.task_label.setText(self.study.task_text())
        if self.study.task == 0:
            self._show_message(self._intro_html())
        elif self.study.finished:
            self._show_message(self._results_html())
        elif self.view_stack.currentWidget() is not self.plotter.interactor:
            self.view_stack.setCurrentWidget(self.plotter.interactor)
            self.plotter.render()

    def _show_message(self, html: str) -> None:
        self.message.setText(html)
        self.view_stack.setCurrentWidget(self.message)

    def _intro_html(self) -> str:
        paragraphs = "".join(f"<p>{text}</p>" for text in self.study.intro_text().split("\n\n"))
        return (f"<h1>Welcome!</h1>{paragraphs}"
                "<p style='color:#f0cd6c'>Experimenter: press T to start task 1.</p>")

    def _results_html(self) -> str:
        labels = {"done": "Done", "timeout": "Time is up", "skipped": "Skipped"}
        rows = "".join(
            f"<tr><td>{r.task}</td><td>{self.study.tasks[r.task - 1].molecule.capitalize()}</td>"
            f"<td>{labels[r.outcome]}</td><td align='right'>{r.seconds:.1f} s</td>"
            f"<td align='right'>{r.false_triggers}</td></tr>"
            for r in self.study.results)
        done = [r for r in self.study.results if r.outcome == "done"]
        mean = f"{sum(r.seconds for r in done) / len(done):.1f} s" if done else "-"
        return (
            "<h1>All tasks done. Thank you!</h1>"
            f"<p>{self.study.participant} · {self.study.condition}</p>"
            "<table align='center' cellspacing='0' cellpadding='8'>"
            "<tr><th>Task</th><th>Molecule</th><th>Result</th><th>Time</th><th>False triggers</th></tr>"
            f"{rows}</table>"
            f"<p>Completed {len(done)} of {len(self.study.tasks)} tasks · mean time for completed tasks: {mean}</p>"
            f"<p style='color:#9fb0bf; font-size:14px'>Saved as {self.logger.path.parent.name}/{self.logger.path.name}</p>"
        )

    def show_molecule(self, name: str) -> None:
        self.plotter.clear()
        self.molecule = molecule.load(name)
        molecule.add_to_plotter(self.plotter, self.molecule)
        self.controller.set_home()
        self.plotter.render()
        self.molecule_name = name
        self.molecule_box.setCurrentIndex(list(molecule.MOLECULES).index(name))
        self.setWindowTitle(f"HandsOn Molecules - {name}")
        self.logger.log("molecule", name)

    def _step_molecule(self, step: int) -> None:
        names = list(molecule.MOLECULES)
        self.show_molecule(names[(names.index(self.molecule_name) + step) % len(names)])

    def _tick(self) -> None:
        if self.study and self.study.running:
            self._check_task()
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
            if self._tracking != "detected":
                self._tracking = "detected"
                self.logger.log("hand_detected", frame.handedness or "")
        elif self._tracking == "detected" and frame.timestamp - self._last_hand_time > TRACKING_LOST_AFTER_S:
            self._tracking = "lost"
            self.logger.log("tracking_lost")

        landmarks = self.landmark_filter(frame.landmarks, frame.timestamp)
        height, width = frame.image.shape[:2]
        shape = self.gestures.update(landmarks, aspect=width / height)
        if shape != self._last_shape:
            self.logger.log("gesture", shape.value)
            self._last_shape = shape

        action = self.controller.update(shape, landmarks, now=frame.timestamp)
        if action != self._last_action:
            self.logger.log("action", action)
            self._last_action = action

        self.card.show_view(card_view(self._tracking, shape, action))
        self.card.set_progress(self.controller.hold_progress)
        self.legend.highlight(shape)

    def _show_preview(self, rgb) -> None:
        height, width, _ = rgb.shape
        image = QImage(rgb.data, width, height, 3 * width, QImage.Format.Format_RGB888).copy()
        self.preview.setPixmap(QPixmap.fromImage(image).scaled(
            *PREVIEW_SIZE, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def closeEvent(self, event) -> None:
        self.timer.stop()
        if self.tracker:
            self.tracker.stop()
        self.logger.log("app_exit")
        self.logger.close()
        self.plotter.close()
        super().closeEvent(event)
