#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera la captura real de la app para la web.

    .venv\\Scripts\\python.exe captura_web.py

Abre la ventana fuera de la pantalla visible, la rellena con una playlist de
ejemplo y guarda `assets/app-v1.webp` + un PNG de reserva.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, QTimer, Qt
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter
from PySide6.QtWidgets import QApplication

import app_pyside as a
import engine

RAIZ = Path(__file__).resolve().parent
SALIDA = RAIZ / "assets"


def portada() -> bytes:
    """Portada abstracta cálida, para no depender de internet."""
    img = QImage(700, 700, QImage.Format_RGB32)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)

    base = QLinearGradient(0, 0, 700, 700)
    base.setColorAt(0.0, QColor("#3a2416"))
    base.setColorAt(0.55, QColor("#20130f"))
    base.setColorAt(1.0, QColor("#140d0c"))
    p.fillRect(0, 0, 700, 700, base)

    for cx, cy, radio, color in (
        (210, 190, 320, QColor(255, 220, 172, 150)),
        (540, 520, 360, QColor(232, 112, 91, 170)),
        (640, 120, 240, QColor(242, 169, 78, 90)),
    ):
        luz = QLinearGradient(cx - radio, cy - radio, cx + radio, cy + radio)
        luz.setColorAt(0.0, color)
        luz.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))
        p.setPen(Qt.NoPen)
        p.setBrush(luz)
        p.drawEllipse(cx - radio, cy - radio, radio * 2, radio * 2)

    p.end()

    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    img.save(buffer, "PNG")
    return bytes(buffer.data())


def playlist_demo() -> engine.Playlist:
    titulos = [
        ("Solo sex", 193, "v4.5", "synthwave, dream pop"),
        ("Brisa lenta", 178, "v4.5", "chill, lofi"),
        ("Última luz", 227, "v4", "indie, emocional"),
        ("Costa Norte", 205, "v4.5", "ambient"),
        ("Sin señal", 241, "v4", "rock alternativo"),
    ]
    pistas = [
        engine.Track(
            id=f"demo-{i}", index=i + 1, title=t, duration=d,
            model=m, tags=g, created="2026-10-24", cover="",
        )
        for i, (t, d, m, g) in enumerate(titulos)
    ]
    return engine.Playlist(
        id="demo-playlist",
        name="Nocturno en la costa",
        author="dancenot02",
        handle="dancenot02",
        total_duration=sum(d for _, d, _, _ in titulos),
        tracks=pistas,
    )


def main() -> int:
    app = QApplication(sys.argv)
    app.setFont(a.f(9.5))
    app.setQuitOnLastWindowClosed(False)

    engine.push_history = lambda *_a, **_k: None  # no ensuciar el historial real
    a.SETTINGS.setValue("tray", False)

    win = a.MainWindow()
    win.resize(1200, 820)
    win._on_preview([playlist_demo()])
    win._on_cover(portada())
    win.seg_fmt.setCurrent("mp3")
    win.move(-4000, 0)
    win.show()

    def guardar() -> None:
        SALIDA.mkdir(parents=True, exist_ok=True)
        pix = win.grab()
        pix.save(str(SALIDA / "app-v1.png"), "PNG")
        ok = pix.save(str(SALIDA / "app-v1.webp"), "WEBP", 92)
        print(f"captura {pix.width()}x{pix.height()} px · webp={ok}")
        app.quit()

    QTimer.singleShot(1200, guardar)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
