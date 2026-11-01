#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mi Suno — interfaz PySide6 v2.

Glassmorphism + bento grid. Vista previa con selección de pistas, formatos,
metadatos, ajustes, bandeja y atajos.

Núcleo MIT © zarigata — https://github.com/zarigata/sudodownloader
"""

from __future__ import annotations

import math
import json
import ctypes
import os
import re
import sys
import tempfile
import threading
from pathlib import Path

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QEvent,
    QObject,
    QPoint,
    QPropertyAnimation,
    QRectF,
    QSettings,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QIcon,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizeGrip,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

import engine
import requests

# ---------------------------------------------------------------- paleta ----
BG = QColor("#0A0A0C")
TEXT = QColor("#F4F4F7")
TEXT2 = QColor("#9A9AA4")
TEXT3 = QColor("#61616B")
ACCENT = QColor("#F2A94E")
ACCENT2 = QColor("#E8705B")
OK = QColor("#5FBF8F")
WARN = QColor("#E8B15C")
BAD = QColor("#E06C6C")

RADIUS = 22
SETTINGS = QSettings("MiSuno", "MiSuno")
APP_VERSION = "1.2.2"
# Canal de actualizaciones: el JSON que sirve GitHub Pages junto a la web.
UPDATE_FEED = "https://dancenot0.github.io/Suno-music-downleader/version.json"


def _vtuple(text: str) -> tuple[int, ...]:
    """'1.2.3' -> (1, 2, 3) para comparar versiones."""
    nums = re.findall(r"\d+", str(text))
    return tuple(int(n) for n in nums[:4])


def f(size: float, weight=QFont.Normal, spacing: float = 0.0) -> QFont:
    font = QFont("Segoe UI Variable Display")
    if not font.exactMatch():
        font = QFont("Segoe UI")
    font.setPointSizeF(size)
    font.setWeight(weight)
    if spacing:
        font.setLetterSpacing(QFont.AbsoluteSpacing, spacing)
    return font


def label(text: str, size=9.5, weight=QFont.Normal, color=TEXT2) -> QLabel:
    w = QLabel(text)
    w.setFont(f(size, weight))
    w.setStyleSheet(f"color: rgba({color.red()},{color.green()},{color.blue()},{color.alpha()});")
    return w


def chip(text: str, color=ACCENT, size=8) -> QLabel:
    w = QLabel(text)
    w.setFont(f(size, QFont.DemiBold))
    w.setFixedHeight(20)
    w.setAlignment(Qt.AlignCenter)
    w.setStyleSheet(
        f"color: rgba({color.red()},{color.green()},{color.blue()},220);"
        f"background: rgba({color.red()},{color.green()},{color.blue()},28);"
        f"border: 1px solid rgba({color.red()},{color.green()},{color.blue()},60);"
        "border-radius: 8px; padding: 0 6px;"
    )
    return w


def mmss(seconds: float) -> str:
    try:
        s = int(seconds)
    except (TypeError, ValueError):
        return "--:--"
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def human_speed(bps: float) -> str:
    for unit in ("B/s", "KB/s", "MB/s"):
        if bps < 1024 or unit == "MB/s":
            return f"{bps:.0f} {unit}" if unit == "B/s" else f"{bps:.1f} {unit}"
        bps /= 1024.0
    return ""


# ------------------------------------------------------------- backdrop ----
class Backdrop(QWidget):
    ORBS = [
        (0.12, 0.02, 0.62, QColor(242, 169, 78, 48)),
        (0.94, 0.18, 0.58, QColor(232, 112, 91, 40)),
        (0.70, 1.04, 0.70, QColor(74, 140, 138, 34)),
        (0.02, 0.86, 0.48, QColor(120, 96, 160, 22)),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._t = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(60)

    def _tick(self):
        self._t += 0.012
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        # Maximizada: esquinas rectas para no dejar huecos contra el borde de la pantalla.
        win = self.window()
        maxed = bool(win and win.isMaximized())
        radius = 0.0 if maxed else float(RADIUS)
        margin = 0.0 if maxed else 0.5
        outer = QRectF(self.rect()).adjusted(margin, margin, -margin, -margin)
        path = QPainterPath()
        if maxed:
            path.addRect(outer)
        else:
            path.addRoundedRect(outer, radius, radius)
        p.setClipPath(path)
        p.fillPath(path, BG)

        w, h = self.width(), self.height()
        for i, (x, y, r, color) in enumerate(self.ORBS):
            dx = math.sin(self._t + i * 1.7) * 0.035
            dy = math.cos(self._t * 0.8 + i) * 0.03
            cx, cy = (x + dx) * w, (y + dy) * h
            radius = r * max(w, h)
            grad = QRadialGradient(cx, cy, radius)
            grad.setColorAt(0.0, color)
            grad.setColorAt(0.55, QColor(color.red(), color.green(), color.blue(), color.alpha() // 3))
            grad.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))
            p.setPen(Qt.NoPen)
            p.setBrush(grad)
            p.drawEllipse(QRectF(cx - radius, cy - radius, radius * 2, radius * 2))

        shade = QLinearGradient(0, h * 0.45, 0, h)
        shade.setColorAt(0.0, QColor(0, 0, 0, 0))
        shade.setColorAt(1.0, QColor(0, 0, 0, 110))
        p.fillPath(path, shade)

        p.setClipping(False)
        if not maxed:
            p.setPen(QPen(QColor(255, 255, 255, 18), 1))
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)


# ---------------------------------------------------------------- card ----
class GlassCard(QWidget):
    def __init__(self, radius=RADIUS, parent=None):
        super().__init__(parent)
        self.radius = radius
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(r, self.radius, self.radius)
        body = QLinearGradient(0, 0, 0, self.height())
        body.setColorAt(0.0, QColor(255, 255, 255, 20))
        body.setColorAt(1.0, QColor(255, 255, 255, 9))
        p.fillPath(path, body)
        inner = QPainterPath()
        inner.addRoundedRect(r.adjusted(1, 1, -1, -1), self.radius - 1, self.radius - 1)
        p.fillPath(inner, QColor(255, 255, 255, 5))
        p.setPen(QPen(QColor(255, 255, 255, 24), 1))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)


def add_shadow(widget: QWidget, blur=46, dy=16, a=120):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, dy)
    effect.setColor(QColor(0, 0, 0, a))
    widget.setGraphicsEffect(effect)


# --------------------------------------------------------------- button ----
class Button(QPushButton):
    def __init__(self, text="", variant="ghost", parent=None):
        super().__init__(text, parent)
        self.variant = variant
        self._hover = 0.0
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(38)
        self.setFont(f(9.5, QFont.DemiBold))
        self._anim = QPropertyAnimation(self, b"hover", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    def get_hover(self):
        return self._hover

    def set_hover(self, v):
        self._hover = v
        self.update()

    hover = Property(float, get_hover, set_hover)

    def enterEvent(self, e):
        self._anim.stop()
        self._anim.setStartValue(self._hover)
        self._anim.setEndValue(1.0)
        self._anim.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._anim.stop()
        self._anim.setStartValue(self._hover)
        self._anim.setEndValue(0.0)
        self._anim.start()
        super().leaveEvent(e)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        h = self._hover if self.isEnabled() else 0.0

        if self.variant == "primary":
            c1 = ACCENT.lighter(100 + int(14 * h))
            c2 = ACCENT2.lighter(100 + int(10 * h))
            if self.isDown():
                c1, c2 = ACCENT.darker(112), ACCENT2.darker(112)
            if h > 0.02:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(242, 169, 78, int(40 * h)))
                p.drawRoundedRect(r.adjusted(-3, -3, 3, 3), 15, 15)
            grad = QLinearGradient(r.topLeft(), r.bottomRight())
            grad.setColorAt(0.0, c1)
            grad.setColorAt(1.0, c2)
            p.setPen(Qt.NoPen)
            p.setBrush(grad)
            p.drawRoundedRect(r, 12, 12)
            p.setPen(QColor("#1C1305"))
        elif self.variant == "ghost":
            p.setPen(QPen(QColor(255, 255, 255, 28 + int(18 * h)), 1))
            p.setBrush(QColor(255, 255, 255, 10 + int(8 * h)))
            p.drawRoundedRect(r, 12, 12)
            p.setPen(TEXT if self.isEnabled() else TEXT3)
        else:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, int(14 * h)))
            p.drawRoundedRect(r, 10, 10)
            p.setPen(TEXT2 if self.isEnabled() else TEXT3)

        p.setFont(self.font())
        p.drawText(r, Qt.AlignCenter, self.text())


class GlyphButton(QPushButton):
    """Botón de icono dibujado: reloj, sliders, carpeta, actualizar, descargar."""

    def __init__(self, kind, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.setFixedSize(34, 30)
        self.setCursor(Qt.PointingHandCursor)
        self._hover = False
        self._angle = 0.0
        self._spin = QTimer(self)
        self._spin.setInterval(40)
        self._spin.timeout.connect(self._tick)

    def set_kind(self, kind: str):
        if kind != self.kind:
            self.kind = kind
            self.update()

    def set_busy(self, on: bool):
        if on:
            if not self._spin.isActive():
                self._spin.start()
        else:
            self._spin.stop()
            self._angle = 0.0
        self.update()

    def _tick(self):
        self._angle = (self._angle + 16.0) % 360.0
        self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self._hover:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 24))
            p.drawRoundedRect(QRectF(self.rect()), 8, 8)
        pen = QPen(QColor("#D6D6DE"), 1.4)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        cx, cy = self.width() / 2, self.height() / 2

        if self.kind == "clock":
            p.drawEllipse(QRectF(cx - 6, cy - 6, 12, 12))
            p.drawLine(QPoint(int(cx), int(cy)), QPoint(int(cx), int(cy - 4)))
            p.drawLine(QPoint(int(cx), int(cy)), QPoint(int(cx + 3), int(cy + 1)))
        elif self.kind == "sliders":
            for dy in (-4, 0, 4):
                p.drawLine(QPoint(int(cx - 6), int(cy + dy)), QPoint(int(cx + 6), int(cy + dy)))
            p.setBrush(QColor("#0A0A0C"))
            for dx, dy in ((-3, -4), (2, 0), (-1, 4)):
                p.drawEllipse(QRectF(cx + dx - 1.6, cy + dy - 1.6, 3.2, 3.2))
        elif self.kind == "folder":
            path = QPainterPath()
            path.moveTo(cx - 6, cy - 3)
            path.lineTo(cx - 2, cy - 3)
            path.lineTo(cx - 0.5, cy - 5)
            path.lineTo(cx + 6, cy - 5)
            path.lineTo(cx + 6, cy + 5)
            path.lineTo(cx - 6, cy + 5)
            path.closeSubpath()
            p.drawPath(path)
        elif self.kind == "refresh":
            # dos flechas circulares
            p.save()
            p.translate(cx, cy)
            p.rotate(self._angle)
            r = 6.0
            for start, span in ((-40, 150), (140, 150)):
                p.drawArc(QRectF(-r, -r, r * 2, r * 2), start * 16, span * 16)
            # puntas de flecha
            for ang, dx, dy in ((105, 1, -1), (-75, -1, 1)):
                p.save()
                p.rotate(ang)
                p.setBrush(QColor("#D6D6DE"))
                p.setPen(Qt.NoPen)
                head = QPainterPath()
                head.moveTo(r, -2.6)
                head.lineTo(r + 3.4, 0)
                head.lineTo(r, 2.6)
                head.closeSubpath()
                p.drawPath(head)
                p.restore()
            p.restore()
        elif self.kind == "download":
            p.drawLine(QPoint(int(cx), int(cy - 6)), QPoint(int(cx), int(cy + 3)))
            p.drawLine(QPoint(int(cx), int(cy + 3)), QPoint(int(cx - 3), int(cy)))
            p.drawLine(QPoint(int(cx), int(cy + 3)), QPoint(int(cx + 3), int(cy)))
            p.drawLine(QPoint(int(cx - 6), int(cy + 6)), QPoint(int(cx + 6), int(cy + 6)))


# -------------------------------------------------------------- stepper ----
class Stepper(QWidget):
    valueChanged = Signal(int)

    def __init__(self, value=2, minimum=0, maximum=60, suffix=" s", parent=None):
        super().__init__(parent)
        self._value = value
        self._min = minimum
        self._max = maximum
        self._suffix = suffix
        self._zone = None
        self.setFixedSize(104, 34)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)

    def value(self) -> int:
        return self._value

    def setValue(self, v: int):
        v = max(self._min, min(self._max, int(v)))
        if v != self._value:
            self._value = v
            self.valueChanged.emit(v)
            self.update()

    def _hit(self, pos):
        if pos.x() < self.width() * 0.3:
            return "min"
        if pos.x() > self.width() * 0.7:
            return "max"
        return None

    def mouseMoveEvent(self, e):
        z = self._hit(e.position())
        if z != self._zone:
            self._zone = z
            self.update()

    def leaveEvent(self, _e):
        self._zone = None
        self.update()

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        z = self._hit(e.position())
        if z == "min":
            self.setValue(self._value - 1)
        elif z == "max":
            self.setValue(self._value + 1)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QPen(QColor(255, 255, 255, 28), 1))
        p.setBrush(QColor(255, 255, 255, 10))
        p.drawRoundedRect(r, 10, 10)
        if self._zone:
            zr = QRectF(r.left() + 2, r.top() + 2, 26, r.height() - 4)
            if self._zone == "max":
                zr.moveLeft(r.right() - 28)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 22))
            p.drawRoundedRect(zr, 8, 8)
        pen = QPen(QColor("#D9D9E0"), 1.4)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        cy = self.height() / 2
        p.drawLine(QPoint(12, int(cy)), QPoint(20, int(cy)))
        px = self.width() - 14
        p.drawLine(QPoint(px - 4, int(cy)), QPoint(px + 4, int(cy)))
        p.drawLine(QPoint(px, int(cy - 4)), QPoint(px, int(cy + 4)))
        p.setPen(QColor("#EDEDF2"))
        p.setFont(f(9, QFont.DemiBold))
        p.drawText(QRectF(0, 0, self.width(), self.height()), Qt.AlignCenter,
                   f"{self._value}{self._suffix}")


# --------------------------------------------------------------- toggle ----
class Toggle(QWidget):
    toggled = Signal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self._knob = 1.0 if checked else 0.0
        self.setFixedSize(44, 26)
        self.setCursor(Qt.PointingHandCursor)
        self._anim = QPropertyAnimation(self, b"knob", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    def get_knob(self):
        return self._knob

    def set_knob(self, v):
        self._knob = v
        self.update()

    knob = Property(float, get_knob, set_knob)

    def isChecked(self):
        return self._checked

    def setChecked(self, value):
        self._checked = bool(value)
        self._anim.stop()
        self._anim.setStartValue(self._knob)
        self._anim.setEndValue(1.0 if self._checked else 0.0)
        self._anim.start()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.setChecked(not self._checked)
            self.toggled.emit(self._checked)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(0, 0, self.width(), self.height())
        track = QColor(
            int(58 + (242 - 58) * self._knob),
            int(58 + (169 - 58) * self._knob),
            int(66 + (78 - 66) * self._knob),
        )
        p.setPen(QPen(QColor(255, 255, 255, 30), 1))
        p.setBrush(track)
        p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), 13, 13)
        d = 18
        x = 4 + (self.width() - d - 8) * self._knob
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 60))
        p.drawEllipse(QRectF(x, 5, d, d))
        p.setBrush(QColor("#FFFFFF") if self._checked else QColor("#D6D6DC"))
        p.drawEllipse(QRectF(x, 4, d, d))


# ------------------------------------------------------------- checkbox ----
class CheckBox(QWidget):
    toggled = Signal(bool)

    def __init__(self, checked=True, parent=None):
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(20, 20)
        self.setCursor(Qt.PointingHandCursor)

    def isChecked(self):
        return self._checked

    def setChecked(self, value):
        self._checked = bool(value)
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.setChecked(not self._checked)
            self.toggled.emit(self._checked)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(1, 1, 18, 18)
        if self._checked:
            grad = QLinearGradient(r.topLeft(), r.bottomRight())
            grad.setColorAt(0.0, ACCENT)
            grad.setColorAt(1.0, ACCENT2)
            p.setPen(Qt.NoPen)
            p.setBrush(grad)
            p.drawRoundedRect(r, 6, 6)
            pen = QPen(QColor("#1C1305"), 1.8)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.drawLine(QPoint(6, 10), QPoint(9, 13))
            p.drawLine(QPoint(9, 13), QPoint(14, 7))
        else:
            p.setPen(QPen(QColor(255, 255, 255, 60), 1.2))
            p.setBrush(QColor(255, 255, 255, 8))
            p.drawRoundedRect(r, 6, 6)


# ------------------------------------------------------------ segmented ----
class Segmented(QWidget):
    changed = Signal(int)

    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.items = items
        self.index = 0
        self._hover = -1
        self.setFixedHeight(34)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)

    def current(self) -> str:
        return self.items[self.index]

    def setCurrent(self, value: str):
        if value in self.items:
            self.index = self.items.index(value)
            self.update()

    def _at(self, pos) -> int:
        if not self.items:
            return -1
        seg = self.width() / len(self.items)
        i = int(pos.x() // seg)
        return max(0, min(len(self.items) - 1, i))

    def mouseMoveEvent(self, e):
        i = self._at(e.position())
        if i != self._hover:
            self._hover = i
            self.update()

    def leaveEvent(self, _e):
        self._hover = -1
        self.update()

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        i = self._at(e.position())
        if i != self.index:
            self.index = i
            self.changed.emit(i)
            self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QPen(QColor(255, 255, 255, 22), 1))
        p.setBrush(QColor(255, 255, 255, 8))
        p.drawRoundedRect(r, 10, 10)
        if not self.items:
            return
        seg = r.width() / len(self.items)
        sel = QRectF(r.left() + seg * self.index + 3, r.top() + 3, seg - 6, r.height() - 6)
        grad = QLinearGradient(sel.topLeft(), sel.bottomRight())
        grad.setColorAt(0.0, QColor(242, 169, 78, 46))
        grad.setColorAt(1.0, QColor(232, 112, 91, 46))
        p.setPen(QPen(QColor(242, 169, 78, 90), 1))
        p.setBrush(grad)
        p.drawRoundedRect(sel, 8, 8)
        p.setFont(f(8.5, QFont.DemiBold))
        for i, item in enumerate(self.items):
            p.setPen(TEXT if i == self.index else TEXT2)
            p.drawText(QRectF(r.left() + seg * i, r.top(), seg, r.height()),
                       Qt.AlignCenter, item.upper())


# ------------------------------------------------------------- progress ----
class Progress(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0.0
        self._indeterminate = False
        self._phase = 0.0
        self.setFixedHeight(10)
        self._anim = QPropertyAnimation(self, b"value", self)
        self._anim.setDuration(420)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def get_value(self):
        return self._value

    def set_value(self, v):
        self._value = max(0.0, min(100.0, v))
        self.update()

    value = Property(float, get_value, set_value)

    def animate_to(self, v):
        self._anim.stop()
        self._anim.setStartValue(self._value)
        self._anim.setEndValue(v)
        self._anim.start()

    def set_indeterminate(self, on: bool):
        self._indeterminate = on
        if on:
            self._timer.start(30)
        else:
            self._timer.stop()
            self.update()

    def _tick(self):
        self._phase = (self._phase + 0.02) % 1.0
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        r = h / 2
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 18))
        p.drawRoundedRect(QRectF(0, 0, w, h), r, r)
        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0.0, ACCENT)
        grad.setColorAt(1.0, ACCENT2)

        if self._indeterminate:
            seg = w * 0.28
            x = (w + seg) * self._phase - seg
            path = QPainterPath()
            path.addRoundedRect(QRectF(0, 0, w, h), r, r)
            p.setClipPath(path)
            p.setBrush(grad)
            p.drawRoundedRect(QRectF(x, 0, seg, h), r, r)
            p.setClipping(False)
            return

        fw = w * self._value / 100.0
        if fw <= 0.5:
            return
        p.setBrush(grad)
        p.drawRoundedRect(QRectF(0, 0, max(fw, h), h), r, r)
        p.setBrush(QColor(255, 255, 255, 150))
        p.drawEllipse(QRectF(fw - 5, 2.5, 5, 5))


# --------------------------------------------------------------- cover ----
class Cover(QWidget):
    def __init__(self, size=54, parent=None):
        super().__init__(parent)
        self._pix = None
        self.setFixedSize(size, size)

    def set_data(self, data: bytes):
        pix = QPixmap()
        if pix.loadFromData(data):
            self._pix = pix
            self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 14, 14)
        p.setClipPath(path)
        if self._pix:
            scaled = self._pix.scaled(self.width(), self.height(), Qt.KeepAspectRatioByExpanding,
                                      Qt.SmoothTransformation)
            p.drawPixmap(0, 0, scaled)
        else:
            grad = QRadialGradient(self.width() * 0.4, self.height() * 0.35, self.width())
            grad.setColorAt(0.0, ACCENT)
            grad.setColorAt(1.0, ACCENT2)
            p.fillPath(path, grad)
            p.setBrush(QColor(10, 10, 12))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QRectF(self.width() / 2 - 8, self.height() / 2 - 8, 16, 16))
        p.setClipping(False)
        p.setPen(QPen(QColor(255, 255, 255, 40), 1))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)


# ------------------------------------------------------------- elided ----
class ElidedLabel(QLabel):
    def __init__(self, text="", color=TEXT, size=9.5, weight=QFont.Normal, parent=None):
        super().__init__(parent)
        self._full = text
        self._color = color
        self.setFont(f(size, weight))
        self.setMinimumWidth(0)

    def setText(self, text):
        self._full = text
        self.update()

    def text(self):
        return self._full

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setPen(self._color)
        p.setFont(self.font())
        fm = p.fontMetrics()
        p.drawText(self.rect(), Qt.AlignVCenter | Qt.AlignLeft,
                   fm.elidedText(self._full, Qt.ElideRight, self.width()))


# ------------------------------------------------------------ track row ----
class TrackRow(QWidget):
    toggled = Signal()

    def __init__(self, track: engine.Track, playlist_name="", show_playlist=False,
                 display_index=None, parent=None):
        super().__init__(parent)
        self.track = track
        self._hover = False
        self.setFixedHeight(46)
        self.setCursor(Qt.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 12, 0)
        lay.setSpacing(10)

        self.check = CheckBox(True)
        self.check.toggled.connect(lambda _v: self.toggled.emit())
        lay.addWidget(self.check)

        num = QLabel(str(display_index if display_index is not None else track.index))
        num.setFont(f(8.5, QFont.DemiBold))
        num.setStyleSheet("color: rgba(120,120,132,220);")
        num.setFixedWidth(22)
        num.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay.addWidget(num)

        title = ElidedLabel(track.title, TEXT, 9.5, QFont.DemiBold)
        lay.addWidget(title, 1)

        if show_playlist:
            lay.addWidget(chip(playlist_name[:18], TEXT3, 7))

        if track.model:
            lay.addWidget(chip(track.model, OK, 7))

        dur = QLabel(mmss(track.duration))
        dur.setFont(f(8.5))
        dur.setStyleSheet("color: rgba(120,120,132,220);")
        dur.setFixedWidth(46)
        dur.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay.addWidget(dur)

    def isChecked(self):
        return self.check.isChecked()

    def setChecked(self, value):
        self.check.setChecked(value)

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.setChecked(not self.isChecked())
            self.toggled.emit()

    def paintEvent(self, _event):
        if self._hover:
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 10))
            p.drawRoundedRect(QRectF(self.rect()).adjusted(2, 1, -2, -1), 10, 10)


# ----------------------------------------------------------- track list ----
class TrackList(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows: list[TrackRow] = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }"
            "QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }"
            "QScrollBar::handle:vertical { background: rgba(255,255,255,0.14);"
            " border-radius: 4px; min-height: 30px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }"
        )
        self.container = QWidget()
        self.container.setAttribute(Qt.WA_TranslucentBackground)
        self.vbox = QVBoxLayout(self.container)
        self.vbox.setContentsMargins(0, 0, 4, 0)
        self.vbox.setSpacing(2)
        self.vbox.addStretch(1)
        self.scroll.setWidget(self.container)
        lay.addWidget(self.scroll)

    def clear(self):
        for row in self.rows:
            row.setParent(None)
        self.rows = []

    def set_rows(self, rows: list[TrackRow]):
        self.clear()
        self.rows = rows
        for row in rows:
            row.toggled.connect(self.changed.emit)
            self.vbox.insertWidget(self.vbox.count() - 1, row)

    def select_all(self, value: bool):
        for row in self.rows:
            row.setChecked(value)
        self.changed.emit()

    def selected_ids(self) -> set[str]:
        return {r.track.id for r in self.rows if r.isChecked()}

    def selected_count(self) -> int:
        return sum(1 for r in self.rows if r.isChecked())

    def apply_filter(self, text: str):
        text = text.strip().lower()
        for row in self.rows:
            hay = f"{row.track.title} {row.track.tags} {row.track.model}".lower()
            row.setVisible(not text or text in hay)


# ----------------------------------------------------------- settings ----
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ajustes")
        self.setModal(True)
        self.setMinimumWidth(430)
        self.setStyleSheet(
            "QDialog { background: #101014; }"
            "QLabel { color: #C9C9D2; }"
            "QLineEdit { background: rgba(255,255,255,0.04);"
            " border: 1px solid rgba(255,255,255,0.09); border-radius: 10px;"
            " padding: 8px 10px; color: #EDEDF2; }"
            "QPushButton { background: rgba(255,255,255,0.06); color: #EDEDF2;"
            " border: 1px solid rgba(255,255,255,0.10); border-radius: 10px;"
            " padding: 8px 16px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.10); }"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(14)

        title = QLabel("Avanzado")
        title.setFont(f(14, QFont.DemiBold))
        title.setStyleSheet("color: #F4F4F7;")
        lay.addWidget(title)

        self.proxy = QLineEdit()
        self.proxy.setPlaceholderText("http://host:8080 o socks5://127.0.0.1:1080")
        lay.addWidget(QLabel("Proxy / VPN"))
        lay.addWidget(self.proxy)

        self.feed = QLineEdit()
        self.feed.setPlaceholderText("https://tu-servidor.com/version.json")
        self.feed.setText(str(SETTINGS.value("update_feed", UPDATE_FEED) or UPDATE_FEED))
        lay.addWidget(QLabel(f"Canal de actualizaciones · versión {APP_VERSION}"))
        lay.addWidget(self.feed)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(10)
        self.delay = Stepper(int(SETTINGS.value("delay", 2)), 0, 60)
        self.conc = Stepper(int(SETTINGS.value("concurrency", 1)), 1, 3, "x")
        self.retries = Stepper(int(SETTINGS.value("retries", 3)), 1, 8, "x")
        self.timeout = Stepper(int(SETTINGS.value("timeout", 60)), 15, 300, " s")
        for i, (txt, w) in enumerate([
            ("Pausa", self.delay), ("Concurrencia", self.conc),
            ("Reintentos", self.retries), ("Timeout", self.timeout),
        ]):
            grid.addWidget(QLabel(txt), i // 2, (i % 2) * 2)
            grid.addWidget(w, i // 2, (i % 2) * 2 + 1)
        lay.addLayout(grid)

        self.notify = Toggle(SETTINGS.value("notify", True, bool))
        self.tray = Toggle(SETTINGS.value("tray", True, bool))
        self.arranque = Toggle(SETTINGS.value("update_startup", True, bool))
        self.auto_update = Toggle(SETTINGS.value("auto_update", True, bool))
        for txt, w in (("Notificaciones al terminar", self.notify),
                       ("Cerrar a la bandeja", self.tray),
                       ("Buscar actualizaciones al iniciar", self.arranque),
                       ("Instalar las actualizaciones sola", self.auto_update)):
            row = QHBoxLayout()
            row.addWidget(QLabel(txt), 1)
            row.addWidget(w)
            lay.addLayout(row)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Cancelar")
        save = QPushButton("Guardar")
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        lay.addLayout(buttons)

    def values(self) -> dict:
        return {
            "proxy": self.proxy.text().strip(),
            "update_feed": self.feed.text().strip(),
            "delay": self.delay.value(),
            "concurrency": self.conc.value(),
            "retries": self.retries.value(),
            "timeout": self.timeout.value(),
            "notify": self.notify.isChecked(),
            "tray": self.tray.isChecked(),
            "update_startup": self.arranque.isChecked(),
            "auto_update": self.auto_update.isChecked(),
        }


# ------------------------------------------------------------- title bar ----
class Logo(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 30)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(2, 2, 26, 26)
        grad = QRadialGradient(rect.center(), 16)
        grad.setColorAt(0.0, ACCENT.lighter(112))
        grad.setColorAt(1.0, ACCENT2)
        p.setPen(Qt.NoPen)
        p.setBrush(grad)
        p.drawEllipse(rect)
        p.setBrush(QColor(10, 10, 12))
        p.drawEllipse(QRectF(rect.center().x() - 4, rect.center().y() - 4, 8, 8))


class WindowButton(QPushButton):
    def __init__(self, kind, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.setFixedSize(34, 26)
        self.setCursor(Qt.PointingHandCursor)
        self._hover = False

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self._hover:
            color = QColor(224, 108, 108, 210) if self.kind == "close" else QColor(255, 255, 255, 26)
            p.setPen(Qt.NoPen)
            p.setBrush(color)
            p.drawRoundedRect(QRectF(self.rect()), 7, 7)
        pen = QPen(QColor("#FFFFFF") if (self._hover and self.kind == "close") else QColor("#EDEDF2"), 1.4)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        cx, cy = self.width() / 2, self.height() / 2
        if self.kind == "min":
            p.drawLine(QPoint(int(cx - 5), int(cy)), QPoint(int(cx + 5), int(cy)))
        elif self.kind == "max":
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(QRectF(cx - 5, cy - 5, 10, 10), 2, 2)
        elif self.kind == "restore":
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(QRectF(cx - 5.5, cy - 3.5, 8, 8), 2, 2)
            p.drawRoundedRect(QRectF(cx - 2.5, cy - 5.5, 8, 8), 2, 2)
        else:
            p.drawLine(QPoint(int(cx - 4), int(cy - 4)), QPoint(int(cx + 4), int(cy + 4)))
            p.drawLine(QPoint(int(cx + 4), int(cy - 4)), QPoint(int(cx - 4), int(cy + 4)))


class TitleBar(QWidget):
    def __init__(self, window, parent=None):
        super().__init__(parent)
        self._win = window
        self._drag = None
        self.setFixedHeight(56)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 0, 12, 0)
        lay.setSpacing(8)
        lay.addWidget(Logo())

        names = QVBoxLayout()
        names.setSpacing(0)
        names.addWidget(label("Mi Suno", 10.5, QFont.DemiBold, TEXT))
        names.addWidget(label("descargador de playlists", 8, QFont.Normal, TEXT3))
        lay.addLayout(names)
        lay.addStretch(1)

        self.btn_history = GlyphButton("clock")
        self.btn_update = GlyphButton("refresh")
        self.btn_settings = GlyphButton("sliders")
        self.btn_update.setToolTip("Buscar actualizaciones")
        self.btn_update.clicked.connect(lambda: window._check_update())
        self.btn_min = WindowButton("min")
        self.btn_max = WindowButton("max")
        self.btn_close = WindowButton("close")
        self.btn_min.clicked.connect(window.showMinimized)
        self.btn_max.clicked.connect(self._toggle_max)
        self.btn_close.clicked.connect(window.close)
        for b in (self.btn_history, self.btn_update, self.btn_settings,
                  self.btn_min, self.btn_max, self.btn_close):
            lay.addWidget(b)

    def set_maximized_glyph(self, maximized: bool):
        self.btn_max.kind = "restore" if maximized else "max"
        self.btn_max.update()

    def _toggle_max(self):
        if self._win.isMaximized():
            self._win.showNormal()
        else:
            self._win.showMaximized()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag = e.globalPosition().toPoint() - self._win.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag is not None and e.buttons() & Qt.LeftButton:
            self._win.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, _e):
        self._drag = None

    def mouseDoubleClickEvent(self, _e):
        self._toggle_max()


# ---------------------------------------------------------------- bridge ----
class Bridge(QObject):
    log = Signal(str)
    status = Signal(str)
    progress = Signal(float)
    track = Signal(str, float, float)
    done = Signal(object)
    preview = Signal(object)
    preview_error = Signal(str)
    cover = Signal(object)
    update_info = Signal(object)
    update_ready = Signal(str)
    update_error = Signal(str)


# ------------------------------------------------------------------ app ----
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mi Suno")
        self.setMinimumSize(1060, 740)
        self.resize(1200, 820)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.Window
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
        )
        self.setAcceptDrops(True)

        self.bridge = Bridge()
        self.bridge.log.connect(self._on_log)
        self.bridge.status.connect(self._on_status)
        self.bridge.progress.connect(self._on_progress)
        self.bridge.track.connect(self._on_track)
        self.bridge.done.connect(self._on_done)
        self.bridge.preview.connect(self._on_preview)
        self.bridge.preview_error.connect(self._on_preview_error)
        self.bridge.cover.connect(self._on_cover)
        self.bridge.update_info.connect(self._on_update_info)
        self.bridge.update_ready.connect(self._on_update_ready)
        self.bridge.update_error.connect(self._on_update_error)

        self.state = "idle"
        self.playlists: list[engine.Playlist] = []
        self.engine: engine.Engine | None = None
        self.last_result: dict | None = None
        self._quitting = False
        self._tray = None
        self._update_busy = False
        self._update_silent = False
        self._update_url = ""
        self._update_ver = ""
        self._update_pendiente = ""

        self._build()
        self._load_settings()
        self._build_tray()
        self._shortcuts()
        self._set_state("idle")

        # Busca actualizaciones al arrancar, en silencio (no avisa si ya estás al día).
        if SETTINGS.value("update_startup", True, bool):
            QTimer.singleShot(2500, lambda: self._check_update(silent=True))

    # ------------------------------------------------------------- build --
    def _card(self):
        card = GlassCard()
        add_shadow(card)
        return card

    def _build(self):
        root = Backdrop()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.titlebar = TitleBar(self)
        self.titlebar.btn_settings.clicked.connect(self._open_settings)
        self.titlebar.btn_history.clicked.connect(self._show_history)
        outer.addWidget(self.titlebar)

        content = QWidget()
        content.setAttribute(Qt.WA_TranslucentBackground)
        grid = QGridLayout(content)
        grid.setContentsMargins(20, 6, 20, 20)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        grid.setColumnStretch(0, 7)
        grid.setColumnStretch(1, 5)
        grid.setRowStretch(0, 0)
        grid.setRowStretch(1, 1)
        grid.setRowStretch(2, 0)

        grid.addWidget(self._playlist_card(), 0, 0, 2, 1)
        grid.addWidget(self._dest_card(), 0, 1)
        grid.addWidget(self._output_card(), 1, 1)
        grid.addWidget(self._progress_card(), 2, 0, 1, 2)
        outer.addWidget(content, 1)

        self.grip = QSizeGrip(root)
        self.grip.setFixedSize(18, 18)

    def _playlist_card(self):
        card = self._card()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(12)

        head = QHBoxLayout()
        head.addWidget(label("Playlist", 13, QFont.DemiBold, TEXT))
        self.chip_kind = chip("público")
        head.addWidget(self.chip_kind)
        head.addStretch(1)
        self.btn_change = Button("Cambiar", "quiet")
        self.btn_change.setFixedWidth(78)
        self.btn_change.clicked.connect(self._back_to_input)
        head.addWidget(self.btn_change)
        lay.addLayout(head)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._input_page())
        self.stack.addWidget(self._preview_page())
        lay.addWidget(self.stack, 1)

        foot = QHBoxLayout()
        foot.setSpacing(8)
        self.btn_back = Button("Volver", "ghost")
        self.btn_back.setFixedWidth(88)
        self.btn_back.clicked.connect(self._back_to_input)
        self.btn_open = Button("Abrir carpeta", "ghost")
        self.btn_open.setFixedWidth(128)
        self.btn_open.clicked.connect(self._open_folder)
        self.btn_paste = Button("Pegar", "ghost")
        self.btn_paste.setFixedWidth(88)
        self.btn_paste.clicked.connect(self._paste)
        self.btn_retry = Button("Reintentar", "ghost")
        self.btn_retry.setFixedWidth(112)
        self.btn_retry.clicked.connect(self._retry)
        self.btn_analyze = Button("Analizar", "ghost")
        self.btn_analyze.setFixedWidth(112)
        self.btn_analyze.clicked.connect(self._analyze)
        self.btn_start = Button("Descargar", "primary")
        self.btn_start.setMinimumWidth(150)
        self.btn_start.clicked.connect(lambda: self._start())
        self.btn_pause = Button("Pausar", "ghost")
        self.btn_pause.setFixedWidth(96)
        self.btn_pause.clicked.connect(self._pause)
        self.btn_stop = Button("Detener", "ghost")
        self.btn_stop.setFixedWidth(96)
        self.btn_stop.clicked.connect(self._stop)

        foot.addWidget(self.btn_back)
        foot.addWidget(self.btn_open)
        foot.addWidget(self.btn_paste)
        foot.addStretch(1)
        foot.addWidget(self.btn_retry)
        foot.addWidget(self.btn_analyze)
        foot.addWidget(self.btn_start)
        foot.addWidget(self.btn_pause)
        foot.addWidget(self.btn_stop)
        lay.addLayout(foot)
        return card

    def _input_page(self):
        page = QWidget()
        page.setAttribute(Qt.WA_TranslucentBackground)
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addWidget(label("Uno o más enlaces de Suno", 9, QFont.Normal, TEXT3))

        self.txt_urls = QPlainTextEdit()
        self.txt_urls.setPlaceholderText(
            "https://suno.com/playlist/…\nhttps://suno.com/song/…\n\n"
            "Pega uno o varios enlaces, uno por línea."
        )
        self.txt_urls.setFont(f(10))
        self.txt_urls.setStyleSheet(
            "QPlainTextEdit { background: rgba(255,255,255,0.03);"
            " border: 1px solid rgba(255,255,255,0.07); border-radius: 14px;"
            " padding: 12px; color: #EDEDF2;"
            " selection-background-color: rgba(242,169,78,90); }"
            "QPlainTextEdit:focus { border: 1px solid rgba(242,169,78,90); }"
        )
        lay.addWidget(self.txt_urls, 1)
        lay.addWidget(label(
            "Se acepta el enlace completo o el ID. Arrastra enlaces aquí.",
            8, QFont.Normal, TEXT3))
        return page

    def _preview_page(self):
        page = QWidget()
        page.setAttribute(Qt.WA_TranslucentBackground)
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        head = QHBoxLayout()
        head.setSpacing(12)
        self.cover = Cover(56)
        head.addWidget(self.cover)
        info = QVBoxLayout()
        info.setSpacing(2)
        self.lbl_pl_name = ElidedLabel("", TEXT, 11, QFont.DemiBold)
        self.lbl_pl_meta = ElidedLabel("", TEXT3, 8.5)
        info.addWidget(self.lbl_pl_name)
        info.addWidget(self.lbl_pl_meta)
        head.addLayout(info, 1)
        self.btn_all = Button("Todo", "quiet")
        self.btn_all.setFixedWidth(62)
        self.btn_all.clicked.connect(lambda: self._select_all(True))
        self.btn_none = Button("Nada", "quiet")
        self.btn_none.setFixedWidth(62)
        self.btn_none.clicked.connect(lambda: self._select_all(False))
        head.addWidget(self.btn_all)
        head.addWidget(self.btn_none)
        lay.addLayout(head)

        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filtrar pistas…")
        self.filter.setFont(f(9))
        self.filter.setStyleSheet(
            "QLineEdit { background: rgba(255,255,255,0.03);"
            " border: 1px solid rgba(255,255,255,0.07); border-radius: 10px;"
            " padding: 7px 10px; color: #D9D9E0; }"
        )
        self.filter.textChanged.connect(lambda t: self.track_list.apply_filter(t))
        lay.addWidget(self.filter)

        self.track_list = TrackList()
        self.track_list.changed.connect(self._update_selection)
        lay.addWidget(self.track_list, 1)

        self.lbl_selection = label("", 8, QFont.Normal, TEXT3)
        lay.addWidget(self.lbl_selection)
        return page

    def _dest_card(self):
        card = self._card()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(22, 18, 22, 18)
        lay.setSpacing(8)
        lay.addWidget(label("Destino", 13, QFont.DemiBold, TEXT))

        row = QHBoxLayout()
        row.setSpacing(8)
        self.txt_out = QLineEdit()
        self.txt_out.setFont(f(9))
        self.txt_out.setStyleSheet(
            "QLineEdit { background: rgba(255,255,255,0.03);"
            " border: 1px solid rgba(255,255,255,0.07); border-radius: 10px;"
            " padding: 8px 10px; color: #D9D9E0; }"
        )
        btn = Button("Elegir", "ghost")
        btn.setFixedWidth(74)
        btn.clicked.connect(self._pick_dir)
        self.btn_folder = GlyphButton("folder")
        self.btn_folder.clicked.connect(self._open_folder)
        row.addWidget(self.txt_out, 1)
        row.addWidget(btn)
        row.addWidget(self.btn_folder)
        lay.addLayout(row)
        return card

    def _output_card(self):
        card = self._card()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(22, 18, 22, 18)
        lay.setSpacing(10)
        lay.addWidget(label("Salida", 13, QFont.DemiBold, TEXT))

        self.seg_fmt = Segmented(["m4a", "mp3", "wav", "flac", "ogg"])
        self.seg_fmt.changed.connect(self._on_format)
        lay.addWidget(self.seg_fmt)

        self.lbl_fmt_hint = label("", 7.5, QFont.Normal, TEXT3)
        lay.addWidget(self.lbl_fmt_hint)

        qrow = QWidget()
        qlay = QHBoxLayout(qrow)
        qlay.setContentsMargins(0, 0, 0, 0)
        qlay.setSpacing(10)
        qlay.addWidget(label("Calidad", 9, QFont.DemiBold, TEXT))
        qlay.addStretch(1)
        self.cmb_quality = QComboBox()
        for key, (txt, _args) in engine.QUALITIES.items():
            self.cmb_quality.addItem(txt, key)
        self.cmb_quality.setFont(f(8.5))
        self.cmb_quality.setFixedWidth(150)
        self.cmb_quality.setStyleSheet(
            "QComboBox { background: rgba(255,255,255,0.03);"
            " border: 1px solid rgba(255,255,255,0.07); border-radius: 10px;"
            " padding: 6px 10px; color: #D9D9E0; }"
            "QComboBox::drop-down { border: none; width: 16px; }"
            "QComboBox QAbstractItemView { background: #16161b; color: #EDEDF2;"
            " border: 1px solid rgba(255,255,255,0.10);"
            " selection-background-color: rgba(242,169,78,70); }"
        )
        qlay.addWidget(self.cmb_quality)
        self.quality_row = qrow
        lay.addWidget(qrow)

        toggles = QGridLayout()
        toggles.setHorizontalSpacing(14)
        toggles.setVerticalSpacing(8)
        self.tg = {}
        for i, (key, txt, default) in enumerate([
            ("tags", "Etiquetas", True),
            ("cover", "Portada", True),
            ("lyrics", "Letras", True),
            ("aparte", "Archivos aparte", False),
            ("normalize", "Normalizar", False),
            ("video", "Video", False),
        ]):
            sw = Toggle(default)
            self.tg[key] = sw
            toggles.addWidget(sw, i // 2, (i % 2) * 2)
            toggles.addWidget(label(txt, 9, QFont.DemiBold, TEXT), i // 2, (i % 2) * 2 + 1)
        lay.addLayout(toggles)
        nota = label("La portada y la letra van dentro del archivo de música.", 8.2, QFont.Normal, TEXT3)
        nota.setWordWrap(True)
        lay.addWidget(nota)

        lay.addWidget(label("Nombre de archivo", 9, QFont.DemiBold, TEXT))
        self.txt_template = QLineEdit("{n} - {title}")
        self.txt_template.setFont(f(8.5))
        self.txt_template.setStyleSheet(
            "QLineEdit { background: rgba(255,255,255,0.03);"
            " border: 1px solid rgba(255,255,255,0.07); border-radius: 10px;"
            " padding: 7px 10px; color: #D9D9E0; }"
        )
        lay.addWidget(self.txt_template)
        lay.addWidget(label("{n} {title} {artist} {album} {date} {model}",
                            7.5, QFont.Normal, TEXT3))

        lay.addStretch(1)
        self.lbl_ffmpeg = label("", 8, QFont.Normal, TEXT3)
        lay.addWidget(self.lbl_ffmpeg)
        return card

    def _progress_card(self):
        card = self._card()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(22, 16, 22, 16)
        lay.setSpacing(8)

        head = QHBoxLayout()
        self.lbl_status = label("Listo para empezar.", 9.5, QFont.DemiBold, TEXT)
        self.lbl_pct = label("0%", 9, QFont.DemiBold, TEXT3)
        head.addWidget(self.lbl_status, 1)
        head.addWidget(self.lbl_pct)
        lay.addLayout(head)

        self.bar = Progress()
        lay.addWidget(self.bar)

        line = QHBoxLayout()
        self.lbl_track = ElidedLabel("", TEXT2, 8.5)
        self.lbl_speed = label("", 8, QFont.Normal, TEXT3)
        line.addWidget(self.lbl_track, 1)
        line.addWidget(self.lbl_speed)
        lay.addLayout(line)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(600)
        self.log.setFixedHeight(66)
        self.log.setFont(QFont("Cascadia Mono", 8))
        self.log.setStyleSheet(
            "QPlainTextEdit { background: transparent; border: none;"
            " color: rgba(185,185,195,200); padding: 0; }"
        )
        lay.addWidget(self.log)
        return card

    # ------------------------------------------------------------ estado --
    def _set_state(self, state: str):
        self.state = state
        idle = state == "idle"
        preview = state in ("preview", "done")
        running = state in ("running", "paused")

        self.stack.setCurrentIndex(0 if idle else 1)
        self.btn_change.setVisible(not idle)
        self.btn_paste.setVisible(idle)
        self.btn_analyze.setVisible(idle)
        self.btn_back.setVisible(preview)
        self.btn_start.setVisible(preview)
        self.btn_open.setVisible(preview)
        self.btn_retry.setVisible(state == "done" and bool(self._failed_ids()))
        self.btn_pause.setVisible(running)
        self.btn_stop.setVisible(running)

        self.btn_start.setEnabled(preview)
        self.btn_pause.setEnabled(running)
        self.txt_urls.setEnabled(idle)
        self.btn_change.setEnabled(not running)
        self.btn_analyze.setEnabled(idle)
        self.btn_paste.setEnabled(idle)

    def _failed_ids(self) -> list:
        if not self.last_result:
            return []
        return self.last_result.get("failed") or []

    # ------------------------------------------------------------- acciones --
    def _paste(self):
        text = QApplication.clipboard().text().strip()
        if text:
            current = self.txt_urls.toPlainText().strip()
            self.txt_urls.setPlainText((current + "\n" + text).strip() if current else text)

    def _pick_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Elegir carpeta", self.txt_out.text())
        if path:
            self.txt_out.setText(path)
            SETTINGS.setValue("outdir", path)

    def _open_folder(self):
        folder = None
        if self.last_result and self.last_result.get("folders"):
            folder = self.last_result["folders"][0]
        if not folder:
            folder = self.txt_out.text()
        try:
            if folder and Path(folder).exists():
                os.startfile(folder)  # noqa: S606
            elif folder:
                Path(folder).mkdir(parents=True, exist_ok=True)
                os.startfile(folder)  # noqa: S606
        except Exception as e:  # noqa: BLE001
            self._on_status(f"No se pudo abrir: {e}")

    def _back_to_input(self):
        if self.state in ("running", "paused"):
            return
        self._set_state("idle")

    def _select_all(self, value: bool):
        self.track_list.select_all(value)
        self._update_selection()

    def _update_selection(self):
        total = len(self.track_list.rows)
        sel = self.track_list.selected_count()
        self.lbl_selection.setText(f"{sel} de {total} seleccionadas")

    def _on_format(self, _index):
        fmt = self.seg_fmt.current()
        self.quality_row.setVisible(fmt == "mp3")
        hints = {
            "m4a": "Original de Suno (Opus), sin recomprimir.",
            "mp3": "Compatible con todo; requiere ffmpeg.",
            "wav": "Sin compresión, pero no mejora el Opus de origen.",
            "flac": "Sin pérdida adicional; no recupera el Opus de origen.",
            "ogg": "Opus 160 kbps, más ligero que el MP3.",
        }
        self.lbl_fmt_hint.setText(hints.get(fmt, ""))

    def _open_settings(self):
        dlg = SettingsDialog(self)
        dlg.proxy.setText(SETTINGS.value("proxy", ""))
        if dlg.exec():
            for k, v in dlg.values().items():
                SETTINGS.setValue(k, v)
            self._on_status("Ajustes guardados.")

    # ------------------------------------------------------- actualizaciones --
    def _check_update(self, silent: bool = False):
        """Un botón, dos modos: buscar (flechas) o descargar (flecha abajo).

        Con `silent=True` (al arrancar) no avisa si ya estás al día ni si falla.
        """
        if self._update_busy:
            return
        if self._update_url:
            self._download_update()
            return

        feed = str(SETTINGS.value("update_feed", UPDATE_FEED) or UPDATE_FEED).strip()
        if not feed:
            if not silent:
                self._on_status("Añade la URL del canal de actualizaciones en Ajustes.")
                self._open_settings()
            return

        self._update_busy = True
        self._update_silent = silent
        self.titlebar.btn_update.set_busy(True)
        if not silent:
            self._on_status("Buscando actualizaciones…")

        def work():
            try:
                r = requests.get(
                    feed, timeout=12,
                    headers={"User-Agent": f"MiSuno/{APP_VERSION}"},
                )
                r.raise_for_status()
                # utf-8-sig tolera el BOM que añaden algunos editores.
                self.bridge.update_info.emit(
                    json.loads(r.content.decode("utf-8-sig"))
                )
            except Exception as exc:  # noqa: BLE001
                self.bridge.update_error.emit(str(exc))

        threading.Thread(target=work, daemon=True).start()

    def _on_update_info(self, data):
        self._update_busy = False
        self.titlebar.btn_update.set_busy(False)
        if not isinstance(data, dict):
            self._on_status("El canal de actualizaciones no es válido.")
            return
        ver = str(data.get("version", "")).strip()
        url = str(data.get("url", "")).strip()
        if not ver:
            self._on_status("El canal no indica ninguna versión.")
            return
        if _vtuple(ver) > _vtuple(APP_VERSION):
            self._update_url = url
            self._update_ver = ver
            self.titlebar.btn_update.set_kind("download")
            self.titlebar.btn_update.setToolTip(f"Descargar Suno v1 {ver}")
            automatico = bool(SETTINGS.value("auto_update", True, bool))
            if url and automatico:
                # Al arrancar: se baja y se instala sola, sin preguntar.
                self._on_status(f"Actualizando a la versión {ver}.")
                self._download_update()
            elif url:
                self._on_status(f"Nueva versión {ver} disponible · pulsa la flecha para descargarla.")
            else:
                self._on_status(f"Nueva versión {ver} disponible, pero el canal no trae enlace.")
        else:
            self.titlebar.btn_update.set_kind("refresh")
            self.titlebar.btn_update.setToolTip(f"Al día · versión {APP_VERSION}")
            if not self._update_silent:
                self._on_status(f"Tienes la última versión ({APP_VERSION}).")

    def _on_update_error(self, msg: str):
        self._update_busy = False
        self.titlebar.btn_update.set_busy(False)
        engine.log_to_file(f"actualizacion: {msg}")
        if not self._update_silent:
            self._on_status("No se pudo comprobar la actualización.")

    def _download_update(self):
        url, ver = self._update_url, self._update_ver
        if not url or self._update_busy:
            return
        self._update_busy = True
        self.titlebar.btn_update.set_busy(True)
        self._on_status(f"Descargando Suno v1 {ver}…")
        destino = Path.home() / "Downloads" / f"Suno v1 {ver}.msi"

        def work():
            try:
                destino.parent.mkdir(parents=True, exist_ok=True)
                parcial = destino.with_suffix(".msi.part")
                with requests.get(
                    url, timeout=60, stream=True,
                    headers={"User-Agent": f"MiSuno/{APP_VERSION}"},
                ) as r:
                    r.raise_for_status()
                    total = int(r.headers.get("Content-Length", 0) or 0)
                    hecho = 0
                    with open(parcial, "wb") as fh:
                        for trozo in r.iter_content(262144):
                            if not trozo:
                                continue
                            fh.write(trozo)
                            hecho += len(trozo)
                            if total:
                                self.bridge.status.emit(
                                    f"Descargando actualización… {hecho * 100 // total}%"
                                )
                parcial.replace(destino)
                self.bridge.update_ready.emit(str(destino))
            except Exception as exc:  # noqa: BLE001
                self.bridge.update_error.emit(str(exc))

        threading.Thread(target=work, daemon=True).start()

    def _on_update_ready(self, ruta: str):
        self._update_busy = False
        self.titlebar.btn_update.set_busy(False)
        if self.state in ("running", "paused"):
            # No se corta una descarga a medias: se instala al terminar.
            self._update_pendiente = ruta
            self._on_status("Actualización lista. Se instalará al terminar la descarga.")
            return
        self._instalar_actualizacion(ruta)

    def _instalar_actualizacion(self, ruta: str):
        """Instala el .msi en silencio y vuelve a abrir la app, ya actualizada."""
        self._on_status("Instalando la actualización…")
        if not getattr(sys, "frozen", False):
            # En desarrollo no hay .exe que reinstalar: se abre el instalador.
            try:
                os.startfile(ruta)  # noqa: S606
            except Exception as exc:  # noqa: BLE001
                engine.log_to_file(f"actualizacion: {exc}")
                self._on_status(f"Instalador en {ruta}")
                return
            QTimer.singleShot(900, self._quit)
            return

        exe = sys.executable
        guion = Path(tempfile.gettempdir()) / "suno_v1_actualizar.bat"
        try:
            guion.write_text(
                "@echo off\r\n"
                "ping -n 3 127.0.0.1 >nul\r\n"
                f'msiexec /i "{ruta}" /qn /norestart\r\n'
                f'start "" "{exe}"\r\n',
                encoding="utf-8",
            )
        except OSError as exc:
            engine.log_to_file(f"actualizacion: {exc}")
            self._on_status(f"Instalador en {ruta}")
            return

        codigo = 0
        try:
            # "runas" pide permiso de administrador una vez; luego todo es solo.
            codigo = int(
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", "cmd.exe", f'/c "{guion}"', None, 0
                )
            )
        except Exception as exc:  # noqa: BLE001
            engine.log_to_file(f"actualizacion: {exc}")
        if codigo <= 32:
            # Canceló el aviso de administrador: se deja el instalador a mano.
            self._on_status("Actualización descargada. Falta el permiso de administrador.")
            try:
                os.startfile(ruta)  # noqa: S606
            except Exception:  # noqa: BLE001
                pass
            return
        QTimer.singleShot(700, self._quit)

    def _show_history(self):
        items = engine.read_history()
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: #16161b; color: #EDEDF2;"
            " border: 1px solid rgba(255,255,255,0.10); border-radius: 10px; padding: 6px; }"
            "QMenu::item { padding: 7px 14px; border-radius: 6px; }"
            "QMenu::item:selected { background: rgba(242,169,78,60); }"
        )
        if not items:
            menu.addAction("Sin historial").setEnabled(False)
        for h in items[:12]:
            act = menu.addAction(f"{h.get('name','?')}  ·  {h.get('count',0)} pistas")
            act.triggered.connect(lambda _=False, hid=h.get("id"): self._load_history(hid))
        menu.exec(self.titlebar.btn_history.mapToGlobal(QPoint(0, 34)))

    def _load_history(self, pid: str):
        if not pid or self.state in ("running", "paused"):
            return
        self.txt_urls.setPlainText(f"https://suno.com/playlist/{pid}")
        self._set_state("idle")
        self._analyze()

    # -------------------------------------------------------------- flujo --
    def _targets(self) -> list[str]:
        raw = [ln.strip() for ln in self.txt_urls.toPlainText().splitlines() if ln.strip()]
        return raw

    def _analyze(self):
        raw = self._targets()
        if not raw:
            self._on_status("Pega al menos un enlace.")
            return
        for ln in raw:
            try:
                engine.extract_target(ln)
            except ValueError:
                self._on_status(f"Enlace inválido: {ln[:48]}")
                return

        self._on_status("Analizando…")
        self._set_state("idle")
        self.btn_analyze.setEnabled(False)
        self.btn_paste.setEnabled(False)
        self.bar.set_indeterminate(True)

        proxy = SETTINGS.value("proxy", "")
        timeout = int(SETTINGS.value("timeout", 60))

        def work():
            try:
                pls = [engine.preview(u, proxy, timeout) for u in raw]
                self.bridge.preview.emit(pls)
            except Exception as e:  # noqa: BLE001
                self.bridge.preview_error.emit(str(e))

        threading.Thread(target=work, daemon=True).start()

    def _on_preview(self, playlists):
        self.bar.set_indeterminate(False)
        self.bar.set_value(0)
        self.playlists = playlists
        rows = []
        multi = len(playlists) > 1
        for pl in playlists:
            engine.push_history(pl)
            for t in pl.tracks:
                rows.append(TrackRow(t, pl.name, multi, display_index=len(rows) + 1))
        self.track_list.set_rows(rows)
        self._update_selection()

        first = playlists[0]
        self.lbl_pl_name.setText(f"{len(playlists)} playlists" if multi else first.name)
        if len(playlists) == 1:
            self.lbl_pl_meta.setText(
                f"{first.author or 'Suno'} · {len(first.tracks)} pistas · "
                f"{mmss(first.total_duration)}"
            )
        else:
            self.lbl_pl_meta.setText(
                f"{len(playlists)} playlists · {len(rows)} pistas"
            )
        self.cover._pix = None
        self.cover.update()
        if first.cover:
            self._fetch_cover(first.cover)

        self._set_state("preview")
        self._on_status("Listo para descargar.")
        self._on_log(f"Playlist: {first.name} · {len(rows)} pistas")

    def _on_preview_error(self, msg):
        self.bar.set_indeterminate(False)
        self._set_state("idle")
        self.btn_analyze.setEnabled(True)
        self.btn_paste.setEnabled(True)
        self._on_status(f"No se pudo analizar: {msg}")

    def _on_cover(self, data):
        self.cover.set_data(data)

    def _fetch_cover(self, url):
        def work():
            try:
                import requests
                r = requests.get(url, timeout=20)
                if r.ok:
                    self.bridge.cover.emit(r.content)
            except Exception:  # noqa: BLE001
                pass

        threading.Thread(target=work, daemon=True).start()

    def _options(self) -> engine.Options:
        return engine.Options(
            outdir=self.txt_out.text(),
            fmt=self.seg_fmt.current(),
            quality=self.cmb_quality.currentData(),
            tags=self.tg["tags"].isChecked(),
            cover=self.tg["cover"].isChecked(),
            lyrics=self.tg["lyrics"].isChecked(),
            sidecar=self.tg["aparte"].isChecked(),
            cover_file=self.tg["aparte"].isChecked(),
            lyrics_files=self.tg["aparte"].isChecked(),
            playlist_files=self.tg["aparte"].isChecked(),
            template=self.txt_template.text().strip() or "{n} - {title}",
            normalize=self.tg["normalize"].isChecked(),
            video=self.tg["video"].isChecked(),
            overwrite=False,
            delay=float(SETTINGS.value("delay", 2)),
            concurrency=int(SETTINGS.value("concurrency", 1)),
            proxy=SETTINGS.value("proxy", ""),
            timeout=int(SETTINGS.value("timeout", 60)),
            retries=int(SETTINGS.value("retries", 3)),
        )

    def _selection(self, only: set[str] | None = None) -> dict[str, set[str]]:
        if only is not None:
            result = {}
            for pl in self.playlists:
                ids = {t.id for t in pl.tracks if t.id in only}
                if ids:
                    result[pl.id] = ids
            return result
        selected = self.track_list.selected_ids()
        result = {}
        for pl in self.playlists:
            ids = {t.id for t in pl.tracks if t.id in selected}
            if ids:
                result[pl.id] = ids
        return result

    def _start(self, only: set[str] | None = None):
        if not self.playlists:
            return
        selection = self._selection(only)
        if not selection:
            self._on_status("Selecciona al menos una pista.")
            return

        self.log.clear()
        self.bar.set_indeterminate(False)
        self.bar.set_value(0)
        self.lbl_pct.setText("0%")
        self._set_state("running")
        self.btn_pause.setText("Pausar")

        self.engine = engine.Engine(self._options(), engine.Callbacks(
            log=self.bridge.log.emit,
            status=self.bridge.status.emit,
            progress=self.bridge.progress.emit,
            track=self.bridge.track.emit,
            done=self.bridge.done.emit,
        ))

        def work():
            try:
                self.engine.run(self.playlists, selection)
            except Exception as e:  # noqa: BLE001
                self.bridge.log.emit(f"ERROR: {e}")
                self.bridge.done.emit({"code": 1, "ok": 0, "skipped": 0,
                                       "failed": [], "folders": []})

        threading.Thread(target=work, daemon=True).start()

    def _pause(self):
        if not self.engine:
            return
        if self.state == "running":
            self.engine.pause()
            self._set_state("paused")
            self.btn_pause.setText("Reanudar")
        elif self.state == "paused":
            self.engine.resume()
            self._set_state("running")
            self.btn_pause.setText("Pausar")

    def _stop(self):
        if self.engine:
            self.engine.cancel.set()
            self._on_status("Deteniendo…")

    def _retry(self):
        failed = set(self._failed_ids())
        if not failed:
            return
        self._on_status("Reintentando fallidas…")
        self._start(only=failed)

    # ------------------------------------------------------------- slots ----
    def _on_log(self, msg: str):
        self.log.appendPlainText(msg)
        engine.log_to_file(msg)

    def _on_status(self, msg: str):
        self.lbl_status.setText(msg)

    def _on_progress(self, pct: float):
        if self.bar._indeterminate:
            self.bar.set_indeterminate(False)
        self.bar.animate_to(pct)
        self.lbl_pct.setText(f"{int(round(pct))}%")

    def _on_track(self, title: str, pct: float, speed: float):
        self.lbl_track.setText(title)
        self.lbl_speed.setText(human_speed(speed))

    def _on_done(self, res: dict):
        self.last_result = res
        self.bar.set_indeterminate(False)
        self._set_state("done")
        self.lbl_track.setText("")
        self.lbl_speed.setText("")
        if res.get("cancelled"):
            self._on_status("Detenido." + (" Suno pidió bajar el ritmo." if res.get("blocked") else ""))
        elif res.get("failed"):
            self._on_status(f"Terminado · {res.get('ok', 0)} ok · {len(res['failed'])} fallidas")
            self.bar.animate_to(100)
            self.lbl_pct.setText("100%")
        else:
            self._on_status("Listo.")
            self.bar.animate_to(100)
            self.lbl_pct.setText("100%")
        if SETTINGS.value("notify", True, bool) and self._tray:
            self._tray.showMessage(
                "Mi Suno",
                f"{res.get('ok', 0)} pistas descargadas"
                + (f" · {len(res['failed'])} fallidas" if res.get("failed") else ""),
                QSystemTrayIcon.MessageIcon.Information,
                4000,
            )
        if self._update_pendiente and not self._quitting:
            ruta, self._update_pendiente = self._update_pendiente, ""
            QTimer.singleShot(1200, lambda: self._instalar_actualizacion(ruta))

    # ------------------------------------------------------------- ajustes --
    def _load_settings(self):
        self.txt_out.setText(SETTINGS.value("outdir", str(Path.home() / "Music" / "Suno Downloads")))
        self.seg_fmt.setCurrent(SETTINGS.value("fmt", "mp3"))
        idx = self.cmb_quality.findData(SETTINGS.value("quality", "vbr2"))
        if idx >= 0:
            self.cmb_quality.setCurrentIndex(idx)
        for key, default in (("tags", True), ("cover", True), ("lyrics", True),
                             ("aparte", False), ("normalize", False), ("video", False)):
            self.tg[key].setChecked(SETTINGS.value(key, default, bool))
        self.txt_template.setText(SETTINGS.value("template", "{n} - {title}"))
        self._on_format(0)
        self._refresh_ffmpeg()

    def _save_settings(self):
        SETTINGS.setValue("outdir", self.txt_out.text())
        SETTINGS.setValue("fmt", self.seg_fmt.current())
        SETTINGS.setValue("quality", self.cmb_quality.currentData())
        for key in ("tags", "cover", "lyrics", "aparte", "normalize", "video"):
            SETTINGS.setValue(key, self.tg[key].isChecked())
        SETTINGS.setValue("template", self.txt_template.text())

    def _refresh_ffmpeg(self):
        if engine.locate_ffmpeg():
            self.lbl_ffmpeg.setText("ffmpeg listo · conversión y etiquetas activas")
            self.lbl_ffmpeg.setStyleSheet(f"color: rgba({OK.red()},{OK.green()},{OK.blue()},210);")
        else:
            self.lbl_ffmpeg.setText("sin ffmpeg · solo m4a original")
            self.lbl_ffmpeg.setStyleSheet(f"color: rgba({WARN.red()},{WARN.green()},{WARN.blue()},210);")

    # --------------------------------------------------------------- tray --
    def _build_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        icon = QIcon(str(Path(__file__).resolve().parent / "assets" / "mi_suno.ico"))
        self._tray = QSystemTrayIcon(icon, self)
        menu = QMenu()
        menu.setStyleSheet(
            "QMenu { background: #16161b; color: #EDEDF2;"
            " border: 1px solid rgba(255,255,255,0.10); padding: 6px; }"
            "QMenu::item { padding: 7px 16px; border-radius: 6px; }"
            "QMenu::item:selected { background: rgba(242,169,78,60); }"
        )
        act_show = QAction("Mostrar", self)
        act_show.triggered.connect(self._restore)
        act_open = QAction("Abrir carpeta", self)
        act_open.triggered.connect(self._open_folder)
        act_quit = QAction("Salir", self)
        act_quit.triggered.connect(self._quit)
        menu.addAction(act_show)
        menu.addAction(act_open)
        menu.addSeparator()
        menu.addAction(act_quit)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(
            lambda r: self._restore() if r == QSystemTrayIcon.ActivationReason.Trigger else None
        )
        self._tray.show()

    def _restore(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit(self):
        self._quitting = True
        if self.engine:
            self.engine.cancel.set()
        if self._tray:
            self._tray.hide()
        QApplication.quit()

    def _shortcuts(self):
        for seq, fn in (
            ("Ctrl+Return", self._primary),
            ("Ctrl+O", self._pick_dir),
            ("Ctrl+,", self._open_settings),
            ("Ctrl+F", lambda: self.filter.setFocus()),
        ):
            QShortcut(QKeySequence(seq), self).activated.connect(fn)

    def _primary(self):
        if self.state == "idle":
            self._analyze()
        elif self.state in ("preview", "done"):
            self._start()

    # ------------------------------------------------------------- eventos --
    def _clean_urls(self):
        return [ln.strip() for ln in self.txt_urls.toPlainText().splitlines() if ln.strip()]

    def dragEnterEvent(self, e):
        if e.mimeData().hasText() or e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        text = e.mimeData().text().strip()
        if not text and e.mimeData().hasUrls():
            text = "\n".join(u.toString() for u in e.mimeData().urls())
        if text:
            current = self.txt_urls.toPlainText().strip()
            self.txt_urls.setPlainText((current + "\n" + text).strip() if current else text)
            if self.state == "idle":
                self._on_status("Enlace añadido. Pulsa Analizar.")

    def changeEvent(self, e):
        super().changeEvent(e)
        if e.type() == QEvent.WindowStateChange:
            if hasattr(self, "titlebar"):
                self.titlebar.set_maximized_glyph(self.isMaximized())
            if hasattr(self, "grip"):
                self.grip.setVisible(not self.isMaximized())
            root = self.centralWidget()
            if root is not None:
                root.update()
            return
        if e.type() == QEvent.ActivationChange and self.isActiveWindow():
            if self.state == "idle" and not self.txt_urls.toPlainText().strip():
                clip = QApplication.clipboard().text().strip()
                if "suno.com/" in clip and len(clip) < 400:
                    self._on_status("Enlace de Suno en el portapapeles · pulsa Pegar.")

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "grip"):
            self.grip.move(self.width() - 22, self.height() - 22)

    def closeEvent(self, e):
        self._save_settings()
        if (SETTINGS.value("tray", True, bool) and self._tray and not self._quitting):
            e.ignore()
            self.hide()
            self._tray.showMessage("Mi Suno", "Sigue en la bandeja.",
                                   QSystemTrayIcon.MessageIcon.Information, 2500)
            return
        if self.engine:
            self.engine.cancel.set()
        e.accept()


def main():
    QApplication.setApplicationName("Mi Suno")
    app = QApplication(sys.argv)
    app.setFont(f(9.5))
    app.setQuitOnLastWindowClosed(False)

    def _excepthook(t, v, tb):
        import traceback

        engine.log_to_file("ERROR no controlado:\n" + "".join(traceback.format_exception(t, v, tb)))
        sys.__excepthook__(t, v, tb)

    sys.excepthook = _excepthook

    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MiSuno.Downloader.2")
        except Exception:  # noqa: BLE001
            pass

    icon = Path(__file__).resolve().parent / "assets" / "mi_suno.ico"
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback

        try:
            (Path(__file__).resolve().parent / "error.log").write_text(
                traceback.format_exc(), encoding="utf-8"
            )
        finally:
            raise
