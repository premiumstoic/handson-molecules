"""Step-by-step intro shown in place of the 3D view before the first study task.

The pages come from StudySession.intro_pages(). Back / Next (or the left and right arrow keys)
move between them. On a gesture page, the participant can try the gesture: the page notices
when the camera sees it.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .study import IntroPage

ASSETS = Path(__file__).resolve().parent / "assets"
IMAGE_HEIGHT = 300


class IntroView(QWidget):
    def __init__(self, pages: list[IntroPage], on_page=lambda index: None):
        super().__init__()
        self.setObjectName("intro")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)  # paint the stylesheet background
        self.pages = pages
        self.index = 0
        self.tried: set[str] = set()
        self._on_page = on_page

        self.title = QLabel(objectName="introTitle", alignment=Qt.AlignmentFlag.AlignCenter)
        self.image = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.text = QLabel(objectName="introText", alignment=Qt.AlignmentFlag.AlignCenter, wordWrap=True)
        self.try_label = QLabel(objectName="introTry", alignment=Qt.AlignmentFlag.AlignCenter, wordWrap=True)
        self.note = QLabel("Experimenter: press T to start task 1.", objectName="introNote",
                           alignment=Qt.AlignmentFlag.AlignCenter)
        self.back = QPushButton("◀  Back")
        self.next = QPushButton("Next  ▶")
        self.steps = QLabel(objectName="introSteps", alignment=Qt.AlignmentFlag.AlignCenter)
        for button, step in ((self.back, -1), (self.next, 1)):
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # keep the keys for the window's shortcuts
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, step=step: self.step(step))

        nav = QHBoxLayout()
        nav.addWidget(self.back)
        nav.addStretch()
        nav.addWidget(self.steps)
        nav.addStretch()
        nav.addWidget(self.next)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(60, 40, 60, 30)
        layout.addStretch()
        layout.addWidget(self.title)
        layout.addSpacing(10)
        layout.addWidget(self.image)
        layout.addSpacing(16)
        layout.addWidget(self.text)
        layout.addWidget(self.try_label)
        layout.addWidget(self.note)
        layout.addStretch()
        layout.addLayout(nav)
        self.setStyleSheet("""
            #intro { background: #101a24; }
            QLabel { color: #dde6ee; }
            QLabel#introTitle { font-size: 28px; font-weight: 700; }
            QLabel#introText { font-size: 18px; }
            QLabel#introTry { color: #c5e4df; font-size: 17px; font-weight: 600; padding-top: 10px; }
            QLabel#introNote { color: #f0cd6c; font-size: 17px; font-weight: 600; padding-top: 10px; }
            QLabel#introSteps { color: #9fb0bf; font-size: 14px; }
            QPushButton { color: #101a24; background: #c5e4df; border: none; border-radius: 8px;
                          padding: 10px 22px; font-size: 16px; font-weight: 600; }
            QPushButton:disabled { background: #2b3a48; color: #5d6f80; }
        """)
        self.show_page(0)

    @property
    def page(self) -> IntroPage:
        return self.pages[self.index]

    def step(self, delta: int) -> None:
        index = max(0, min(len(self.pages) - 1, self.index + delta))
        if index != self.index:
            self.show_page(index)

    def show_page(self, index: int) -> None:
        self.index = index
        page = self.page
        self.title.setText(page.title)
        self.text.setText("".join(f"<p>{paragraph}</p>" for paragraph in page.text.split("\n\n")))
        self._show_image(page.image)
        self._show_try()
        last = index == len(self.pages) - 1
        self.note.setVisible(last)
        self.back.setEnabled(index > 0)
        self.next.setVisible(not last)
        self.steps.setText(f"Step {index + 1} of {len(self.pages)}")
        self._on_page(index)

    def gesture_seen(self, gesture: str) -> None:
        """Called with the current hand shape; marks the page's gesture as tried."""
        if gesture == self.page.try_gesture and gesture not in self.tried:
            self.tried.add(gesture)
            self._show_try()

    def _show_try(self) -> None:
        gesture = self.page.try_gesture
        self.try_label.setVisible(bool(gesture))
        if gesture in self.tried:
            self.try_label.setText("✓ That's it! Try it a few more times, then press Next.")
        elif gesture:
            self.try_label.setText("Try it now in front of the camera. The card on the right shows what it sees.")

    def _show_image(self, name: str) -> None:
        path = ASSETS / name if name else None
        if not path or not path.exists():
            self.image.clear()
            self.image.setVisible(False)
            return
        ratio = self.devicePixelRatioF()
        pixmap = QPixmap(str(path)).scaledToHeight(int(IMAGE_HEIGHT * ratio), Qt.TransformationMode.SmoothTransformation)
        pixmap.setDevicePixelRatio(ratio)  # sharp on Retina screens
        self.image.setPixmap(pixmap)
        self.image.setVisible(True)
