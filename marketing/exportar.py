# -*- coding: utf-8 -*-
"""Exporta la agenda de sonidos y los subtítulos que consume la página."""
from __future__ import annotations

import json
from pathlib import Path

from comun import RAIZ, cargar_timeline, lista_sfx, subtitulos

bloques, total = cargar_timeline()
audio = RAIZ / "audio"

efectos = [{"t": round(t, 4), "n": n} for t, n, _ in lista_sfx(bloques)]
(audio / "sfx.json").write_text(json.dumps(efectos, ensure_ascii=False, indent=1), encoding="utf-8")

cartelas = subtitulos(bloques, palabras_por_linea=10, max_caracteres=52)
cartelas = [c for c in cartelas if c["texto"].strip()]
(audio / "subs.json").write_text(json.dumps(cartelas, ensure_ascii=False, indent=1), encoding="utf-8")

print(f"{len(efectos)} sonidos · {len(cartelas)} cartelas · {total:.2f} s")
