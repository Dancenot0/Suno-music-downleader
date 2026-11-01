#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera assets/mi_suno.ico a partir de assets/mi_suno.svg.

Escribe un ICO clásico con entradas BMP de 32 bits (sin depender de Pillow),
que es lo que esperan PyInstaller y Windows para el icono del ejecutable.

Uso:
    .venv\\Scripts\\python.exe build_icon.py
"""

from __future__ import annotations

import os
import struct
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication, QImage, QPainter  # noqa: E402
from PySide6.QtSvg import QSvgRenderer  # noqa: E402

BASE = Path(__file__).resolve().parent
SVG = BASE / "assets" / "mi_suno.svg"
ICO = BASE / "assets" / "mi_suno.ico"
PNG = BASE / "assets" / "mi_suno_512.png"

SIZES = [16, 24, 32, 48, 64, 128, 256]


def render(renderer: QSvgRenderer, size: int) -> QImage:
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)
    renderer.render(p)
    p.end()
    return img


def dib(img: QImage) -> bytes:
    """BITMAPINFOHEADER + píxeles BGRA (de abajo arriba) + máscara AND."""
    img = img.convertToFormat(QImage.Format_ARGB32)
    w, h = img.width(), img.height()
    bpl = img.bytesPerLine()
    raw = bytes(img.bits())

    rows = []
    for y in range(h - 1, -1, -1):
        row = raw[y * bpl : y * bpl + w * 4]
        rows.append(row)
    xor = b"".join(rows)

    and_stride = ((w + 31) // 32) * 4
    and_mask = b"\x00" * (and_stride * h)

    header = struct.pack(
        "<IiiHHIIiiII",
        40,          # biSize
        w,           # biWidth
        h * 2,       # biHeight (XOR + AND)
        1,           # biPlanes
        32,          # biBitCount
        0,           # biCompression = BI_RGB
        len(xor) + len(and_mask),
        0, 0,        # ppm
        0, 0,        # clrUsed / important
    )
    return header + xor + and_mask


def build_ico(images: list[tuple[int, QImage]]) -> bytes:
    count = len(images)
    directory = struct.pack("<HHH", 0, 1, count)
    offset = 6 + 16 * count
    entries = bytearray()
    blobs = []
    for size, img in images:
        data = dib(img)
        dim = 0 if size >= 256 else size
        entries += struct.pack(
            "<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset
        )
        blobs.append(data)
        offset += len(data)
    return directory + bytes(entries) + b"".join(blobs)


def main() -> int:
    if not SVG.exists():
        print(f"No existe {SVG}")
        return 1

    app = QGuiApplication(sys.argv)
    renderer = QSvgRenderer(str(SVG))
    if not renderer.isValid():
        print("SVG inválido")
        return 1

    images = [(s, render(renderer, s)) for s in SIZES]
    ICO.write_bytes(build_ico(images))
    render(renderer, 512).save(str(PNG), "PNG")

    print(f"ICO  -> {ICO}  ({ICO.stat().st_size} bytes, {len(SIZES)} tamanos)")
    print(f"PNG  -> {PNG}")
    app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
