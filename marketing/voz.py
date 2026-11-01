# -*- coding: utf-8 -*-
"""Genera la voz en off con edge-tts y arma la línea de tiempo del video.

Uso:  python marketing/voz.py
Salida: marketing/audio/voz/NN.mp3 (+ .wav), marketing/audio/timeline.json
"""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import edge_tts

RAIZ = Path(__file__).resolve().parent
AUDIO = RAIZ / "audio"
VOZ = AUDIO / "voz"
FFMPEG = RAIZ.parent / "herramientas" / "ffmpeg.exe"

LOCUTOR = "es-MX-JorgeNeural"
RITMO = "+4%"

# Cada bloque = una escena. `min` es la duración mínima en segundos; si la voz
# ocupa más, la escena crece. `cola` deja respirar antes del corte.
BLOQUES = [
    dict(
        id="gancho",
        lineas=["Creas una canción increíble en Suno… y se queda atrapada ahí."],
        minimo=6.6, cola=0.9,
    ),
    dict(
        id="golpe",
        lineas=["Sin archivos. Sin escucharla sin internet. Sin portada. Sin letra."],
        minimo=5.6, cola=0.5,
    ),
    dict(
        id="revelacion",
        lineas=["Hasta ahora. Esto es Suno v1."],
        minimo=5.8, cola=2.0,
    ),
    dict(
        id="escritorio",
        lineas=[
            "Pega el enlace de la playlist. Suno v1 la analiza y te deja elegir.",
            "Un clic… y cada canción aparece en tu carpeta, con su portada y su letra dentro del archivo.",
        ],
        minimo=16.0, cola=0.8,
    ),
    dict(
        id="movil",
        lineas=["En el móvil, igual de simple. Y sin recomprimir: se guarda el archivo original."],
        minimo=10.0, cola=0.4,
    ),
    dict(
        id="potencia",
        lineas=["Pausa, reanuda, reintenta. Hasta tres descargas a la vez. Y nunca te duplica una canción."],
        minimo=9.6, cola=0.4,
    ),
    dict(
        id="pago",
        lineas=["Tu música, en el auto, en el gym, donde quieras."],
        minimo=7.6, cola=0.4,
    ),
    dict(
        id="cierre",
        lineas=["Gratis. Sin cuentas. Sin anuncios. Descarga Suno v1 para Windows y Android."],
        minimo=8.4, cola=1.4,
    ),
]


async def _hablar(texto: str, destino: Path) -> list[dict]:
    """Sintetiza una línea y devuelve sus fronteras de palabra."""
    comunicar = edge_tts.Communicate(texto, LOCUTOR, rate=RITMO, boundary="WordBoundary")
    palabras: list[dict] = []
    with open(destino, "wb") as salida:
        async for trozo in comunicar.stream():
            if trozo["type"] == "audio":
                salida.write(trozo["data"])
            elif trozo["type"] == "WordBoundary":
                palabras.append(
                    {
                        "t": trozo["offset"] / 1e7,
                        "d": trozo["duration"] / 1e7,
                        "p": trozo["text"],
                    }
                )
    return palabras


def _duracion(ruta: Path) -> float:
    salida = subprocess.run(
        [str(FFMPEG), "-i", str(ruta), "-hide_banner"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    ).stderr
    for linea in salida.splitlines():
        if "Duration:" in linea:
            hora, minuto, seg = linea.split("Duration:")[1].split(",")[0].strip().split(":")
            return int(hora) * 3600 + int(minuto) * 60 + float(seg)
    raise RuntimeError(f"sin duración: {ruta}")


def main() -> None:
    VOZ.mkdir(parents=True, exist_ok=True)
    AUDIO.mkdir(parents=True, exist_ok=True)

    bloques = []
    reloj = 0.0
    for indice, bloque in enumerate(BLOQUES):
        lineas = []
        cursor = 0.0
        for j, texto in enumerate(bloque["lineas"]):
            mp3 = VOZ / f"{indice:02d}-{j}.mp3"
            wav = mp3.with_suffix(".wav")
            palabras = asyncio.run(_hablar(texto, mp3))
            subprocess.run(
                [str(FFMPEG), "-y", "-loglevel", "error", "-i", str(mp3),
                 "-ar", "48000", "-ac", "2", str(wav)],
                check=True,
            )
            dur = _duracion(wav)
            lineas.append(
                {
                    "texto": texto,
                    "wav": str(wav.relative_to(RAIZ)).replace("\\", "/"),
                    "inic": cursor,
                    "dur": dur,
                    "palabras": palabras,
                }
            )
            cursor += dur + (0.55 if j < len(bloque["lineas"]) - 1 else 0.0)

        total = max(bloque["minimo"], cursor + bloque["cola"])
        bloques.append(
            {
                "id": bloque["id"],
                "inic": reloj,
                "dur": round(total, 3),
                "voz": lineas,
                "voz_fin": round(cursor, 3),
            }
        )
        reloj += total

    datos = {
        "locutor": LOCUTOR,
        "ritmo": RITMO,
        "total": round(reloj, 3),
        "bloques": bloques,
    }
    (AUDIO / "timeline.json").write_text(
        json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"duracion total: {reloj:.2f} s")
    for b in bloques:
        print(f"  {b['id']:12s} {b['inic']:6.2f} - {b['inic'] + b['dur']:6.2f}  (voz {b['voz_fin']:.2f})")


if __name__ == "__main__":
    sys.exit(main())
