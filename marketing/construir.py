# -*- coding: utf-8 -*-
"""Construye el video completo: voz, música, subtítulos y render.

  python marketing/construir.py            # todo
  python marketing/construir.py --rapido   # calidad de revisión (CRF 22)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
PY = RAIZ.parent / ".venv" / "Scripts" / "python.exe"


def paso(nombre: str, orden: list[str]) -> None:
    print(f"\n== {nombre} ==", flush=True)
    subprocess.run(orden, check=True, cwd=str(RAIZ))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rapido", action="store_true")
    ap.add_argument("--sin-voz", action="store_true")
    args = ap.parse_args()

    if not args.sin_voz or not (RAIZ / "audio" / "timeline.json").exists():
        paso("voz", [str(PY), "voz.py"])

    paso("agenda y subtítulos", [str(PY), "exportar.py"])
    paso("música y efectos", [str(PY), "musica.py"])

    salida = "video/promo-final.mp4" if not args.rapido else "video/promo-prueba.mp4"
    crf = "22" if args.rapido else "15"
    paso("render", [str(PY), "render.py", "--salida", salida, "--crf", crf])
    print(f"\nlisto: marketing/{salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
