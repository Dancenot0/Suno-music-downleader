#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera el arte del instalador (.bmp para WixUI) con la paleta de Mi Suno:
crema cálida, ámbar #F2A94E y coral #E8705B.

    .venv\\Scripts\\python.exe instalador\\hacer_arte.py
"""

from pathlib import Path

from PySide6.QtWidgets import QApplication

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)

SALIDA = Path(__file__).resolve().parent / "arte"
SALIDA.mkdir(parents=True, exist_ok=True)

CREMA = QColor("#FBF5EC")
CREMA2 = QColor("#F3E3CE")
AMBAR = QColor("#F2A94E")
CORAL = QColor("#E8705B")
TINTA = QColor("#1C1305")


def fuente(size: float, weight=QFont.DemiBold, spacing: float = 0.0) -> QFont:
    f = QFont("Segoe UI Variable Display")
    if not f.exactMatch():
        f = QFont("Segoe UI")
    f.setPointSizeF(size)
    f.setWeight(weight)
    if spacing:
        f.setLetterSpacing(QFont.AbsoluteSpacing, spacing)
    return f


def sol(p: QPainter, cx: float, cy: float, r: float):
    grad = QRadialGradient(cx - r * 0.3, cy - r * 0.3, r * 1.4)
    grad.setColorAt(0.0, AMBAR.lighter(112))
    grad.setColorAt(1.0, CORAL)
    p.setPen(Qt.NoPen)
    p.setBrush(grad)
    p.drawEllipse(QPointF(cx, cy), r, r)
    p.setBrush(QColor("#0A0A0C"))
    p.drawEllipse(QPointF(cx, cy), r * 0.34, r * 0.34)


def banner(ruta: Path):
    w, h = 493, 58
    pix = QPixmap(w, h)
    pix.fill(CREMA)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    base = QLinearGradient(0, 0, w, 0)
    base.setColorAt(0.0, CREMA)
    base.setColorAt(0.72, CREMA2)
    base.setColorAt(1.0, QColor("#F7D9B4"))
    p.fillRect(0, 0, w, h, base)

    glow = QRadialGradient(w - 40, h / 2, 120)
    glow.setColorAt(0.0, QColor(242, 169, 78, 70))
    glow.setColorAt(1.0, QColor(242, 169, 78, 0))
    p.setPen(Qt.NoPen)
    p.setBrush(glow)
    p.drawEllipse(QRectF(w - 160, -60, 240, 180))

    sol(p, w - 38, h / 2, 17)

    p.setPen(QPen(QColor(232, 112, 91, 60), 1.2))
    p.setBrush(Qt.NoBrush)
    for i, rr in enumerate((26, 33)):
        p.drawArc(QRectF(w - 38 - rr, h / 2 - rr, rr * 2, rr * 2), 0, 120 * 16)

    p.setFont(fuente(7, QFont.DemiBold, 2.2))
    p.setPen(QColor(120, 100, 78, 190))
    p.drawText(QRectF(0, 0, w - 90, h), Qt.AlignRight | Qt.AlignVCenter, "S U N O   V 1")

    linea = QLinearGradient(0, 0, w, 0)
    linea.setColorAt(0.0, QColor(242, 169, 78, 0))
    linea.setColorAt(0.35, AMBAR)
    linea.setColorAt(1.0, CORAL)
    p.fillRect(QRectF(0, h - 2, w, 2), linea)
    p.end()
    pix.save(str(ruta))


def fondo(ruta: Path):
    w, h = 493, 312
    pix = QPixmap(w, h)
    pix.fill(CREMA)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    base = QLinearGradient(0, 0, 0, h)
    base.setColorAt(0.0, QColor("#FEFAF4"))
    base.setColorAt(1.0, QColor("#F6E8D6"))
    p.fillRect(0, 0, w, h, base)

    glow = QRadialGradient(w - 30, h + 40, 260)
    glow.setColorAt(0.0, QColor(242, 169, 78, 46))
    glow.setColorAt(0.6, QColor(232, 112, 91, 20))
    glow.setColorAt(1.0, QColor(232, 112, 91, 0))
    p.setPen(Qt.NoPen)
    p.setBrush(glow)
    p.drawEllipse(QRectF(w - 300, h - 220, 460, 460))

    # arcos concéntricos muy suaves, como los orbes de la app
    p.setBrush(Qt.NoBrush)
    for i, rr in enumerate((64, 92, 122)):
        p.setPen(QPen(QColor(232, 112, 91, 26 - i * 6), 1.4))
        p.drawArc(QRectF(w - 28 - rr, h + 26 - rr, rr * 2, rr * 2), 40 * 16, 110 * 16)

    sol(p, w - 52, h - 46, 26)

    # pie discreto
    p.setPen(QColor(140, 118, 94, 200))
    p.setFont(fuente(7.5, QFont.Normal, 1.6))
    p.drawText(QRectF(28, h - 26, 260, 16), Qt.AlignLeft | Qt.AlignVCenter,
               "Suno v1 · descargador de playlists")
    p.end()
    pix.save(str(ruta))


def main():
    app = QApplication.instance() or QApplication([])
    # WiX necesita BMP de 24 bits: Qt los escribe directamente.
    banner(SALIDA / "banner.bmp")
    fondo(SALIDA / "fondo.bmp")
    print("arte generado en", SALIDA)
    del app


if __name__ == "__main__":
    main()
