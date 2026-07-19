"""Desktop presence: a floating orb, bottom right.

States: idle (slow breathing, dim blue) / listening (cyan glow) /
thinking (pulsing violet) / speaking (animated rings).

Qt owns the main thread; the assistant's asyncio loop runs in a worker thread
and pushes state changes through a queued signal.
"""

import math
import threading
import time

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QPainter, QRadialGradient
from PySide6.QtWidgets import QApplication, QMenu, QWidget

SIZE = 110

COLORS = {
    "idle": QColor(40, 110, 220),
    "listening": QColor(0, 200, 255),
    "thinking": QColor(150, 80, 255),
    "speaking": QColor(0, 230, 180),
}


class StateBridge(QObject):
    state_changed = Signal(str)


class CortanaOrb(QWidget):
    def __init__(self, bridge: StateBridge):
        super().__init__()
        self.state = "idle"
        self._t0 = time.monotonic()
        self._drag_offset = None

        bridge.state_changed.connect(self._on_state)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(SIZE, SIZE)

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - SIZE - 24, screen.bottom() - SIZE - 24)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(33)  # ~30 fps

    def _on_state(self, state: str):
        self.state = state

    def paintEvent(self, event):
        t = time.monotonic() - self._t0
        color = COLORS.get(self.state, COLORS["idle"])

        if self.state == "idle":
            pulse = 0.72 + 0.06 * math.sin(t * 1.2)          # slow breathing
        elif self.state == "listening":
            pulse = 0.80 + 0.10 * math.sin(t * 5.0)          # attentive glow
        elif self.state == "thinking":
            pulse = 0.70 + 0.16 * math.sin(t * 8.0)          # fast pulse
        else:  # speaking
            pulse = 0.75 + 0.12 * math.sin(t * 10.0) * math.sin(t * 2.3)

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = self.rect().center()
        radius = (SIZE / 2 - 6) * pulse

        # outer glow
        glow = QRadialGradient(center, SIZE / 2)
        gc = QColor(color)
        gc.setAlpha(90)
        glow.setColorAt(0.0, gc)
        gc2 = QColor(color)
        gc2.setAlpha(0)
        glow.setColorAt(1.0, gc2)
        p.setBrush(glow)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(self.rect())

        # core orb
        core = QRadialGradient(center, radius)
        core.setColorAt(0.0, QColor(235, 245, 255))
        core.setColorAt(0.35, color.lighter(130))
        core.setColorAt(1.0, color.darker(140))
        p.setBrush(core)
        p.drawEllipse(center, radius, radius)

        # speaking rings
        if self.state == "speaking":
            ring = QColor(color)
            ring_r = radius + 6 + 5 * abs(math.sin(t * 6.0))
            ring.setAlpha(120)
            p.setBrush(Qt.BrushStyle.NoBrush)
            pen = p.pen()
            pen.setStyle(Qt.PenStyle.SolidLine)
            pen.setColor(ring)
            pen.setWidth(2)
            p.setPen(pen)
            p.drawEllipse(center, ring_r, ring_r)

    # drag to move, right click to quit
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = e.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, e):
        if self._drag_offset is not None:
            self.move(e.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, e):
        self._drag_offset = None

    def contextMenuEvent(self, e):
        menu = QMenu(self)
        quit_action = QAction("Quit Cortana", menu)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)
        menu.exec(e.globalPos())


def run_with_orb(async_entry, shutdown_event=None):
    """Run the Qt orb on the main thread and the assistant loop in a worker.

    async_entry: callable(set_state: Callable[[str], None]) -> coroutine
    shutdown_event: threading.Event shared with the assistant loop - set on
        Ctrl+C so the worker thread's blocking audio calls unwind and its
        own cleanup (e.g. terminating a launched avatar process) actually
        runs, instead of the process exiting out from under it.
    """
    import asyncio
    import signal

    app = QApplication([])
    app.setQuitOnLastWindowClosed(True)
    bridge = StateBridge()
    orb = CortanaOrb(bridge)
    orb.show()

    # stop the ~30fps repaint timer before Qt tears down the window on quit -
    # otherwise a queued timeout can fire after the native window handle is
    # gone, producing a harmless but noisy "QBackingStore::flush() ... does
    # not have a handle" warning
    app.aboutToQuit.connect(orb._timer.stop)

    def handle_sigint(*_):
        # setting this first is what lets the worker thread's finally block
        # (avatar process cleanup, etc.) actually run before we quit Qt
        if shutdown_event is not None:
            shutdown_event.set()
        app.quit()

    # let Ctrl+C in the terminal quit the Qt loop: install a handler and keep
    # a timer running so the Python interpreter gets a chance to deliver it
    signal.signal(signal.SIGINT, handle_sigint)
    sigint_timer = QTimer()
    sigint_timer.timeout.connect(lambda: None)
    sigint_timer.start(200)

    def set_state(state: str):
        bridge.state_changed.emit(state)

    def worker():
        try:
            asyncio.run(async_entry(set_state))
        finally:
            QTimer.singleShot(0, app.quit)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    app.exec()

    # give the worker thread's own cleanup (SHUTDOWN-gated) a bounded chance
    # to finish - e.g. terminating a launched avatar process - before the
    # caller's process-exit logic runs and the daemon thread gets cut off
    thread.join(timeout=8)
