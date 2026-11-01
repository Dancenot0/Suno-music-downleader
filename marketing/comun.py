# -*- coding: utf-8 -*-
"""Piezas compartidas por el render: colores, tipografía, curvas y agenda de SFX."""
from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

RAIZ = Path(__file__).resolve().parent
PROYECTO = RAIZ.parent

ANCHO, ALTO = 1920, 1080
FPS = 30

# ------------------------------------------------------------------ paleta --
FONDO_0 = (9, 6, 5)
FONDO_1 = (28, 19, 16)
AMBAR = (242, 169, 78)
CORAL = (232, 112, 91)
CREMA = (247, 239, 232)
GRIS = (150, 133, 121)
GRIS_OSC = (86, 74, 67)
VERDE = (120, 200, 150)
ROJO = (226, 96, 84)

FUENTES = Path("C:/Windows/Fonts")
_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def fuente(nombre: str, tam: int) -> ImageFont.FreeTypeFont:
    clave = (nombre, tam)
    if clave not in _cache:
        _cache[clave] = ImageFont.truetype(str(FUENTES / nombre), tam)
    return _cache[clave]


def titulo(tam: int):
    return fuente("segoeuib.ttf", tam)


def normal(tam: int):
    return fuente("segoeui.ttf", tam)


def ligera(tam: int):
    return fuente("segoeuil.ttf", tam)


def tecnica(tam: int):
    return fuente("bahnschrift.ttf", tam)


def semibold(tam: int):
    return fuente("segoeuisb.ttf", tam) if (FUENTES / "segoeuisb.ttf").exists() else titulo(tam)


# ------------------------------------------------------------------ curvas --
def limitar(x: float, a: float = 0.0, b: float = 1.0) -> float:
    return a if x < a else b if x > b else x


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def ease_out(t: float) -> float:
    t = limitar(t)
    return 1 - (1 - t) ** 3


def ease_out_expo(t: float) -> float:
    t = limitar(t)
    return 1.0 if t >= 1 else 1 - 2 ** (-10 * t)


def ease_in_out(t: float) -> float:
    t = limitar(t)
    return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_out_back(t: float, s: float = 1.70158) -> float:
    t = limitar(t)
    return 1 + (s + 1) * (t - 1) ** 3 + s * (t - 1) ** 2


def pulso(t: float, centro: float, ancho: float = 0.25) -> float:
    """Campana suave centrada en `centro`."""
    return math.exp(-((t - centro) ** 2) / (2 * ancho * ancho))


def tramo(t: float, a: float, b: float) -> float:
    """0 antes de a, 1 después de b, suave en medio."""
    if b <= a:
        return 1.0 if t >= b else 0.0
    return ease_in_out((t - a) / (b - a))


# ------------------------------------------------------------------ tiempo --
class Linea:
    def __init__(self, datos: dict):
        self.texto: str = datos["texto"]
        self.wav: Path = RAIZ / datos["wav"]
        self.inic: float = datos["inic"]
        self.dur: float = datos["dur"]
        self.palabras: list[dict] = datos.get("palabras", [])
        self._devolver_puntuacion()

    def _devolver_puntuacion(self) -> None:
        """edge-tts devuelve las palabras sin signos: se los reponemos desde el guion."""
        import re

        trozos = re.findall(r"\S+", self.texto)
        if len(trozos) != len(self.palabras):
            return
        for palabra, original in zip(self.palabras, trozos):
            signos = re.search(r"[.,;:!?…]+$", original)
            if signos:
                limpia = palabra["p"].rstrip(".,;:!?…")
                palabra["p"] = limpia + signos.group(0)


class Bloque:
    def __init__(self, datos: dict):
        self.id: str = datos["id"]
        self.inic: float = datos["inic"]
        self.dur: float = datos["dur"]
        self.lineas = [Linea(x) for x in datos["voz"]]
        self.voz_fin: float = datos["voz_fin"]

    @property
    def fin(self) -> float:
        return self.inic + self.dur

    def en(self, t: float) -> float:
        return t - self.inic


def cargar_timeline() -> tuple[list[Bloque], float]:
    datos = json.loads((RAIZ / "audio" / "timeline.json").read_text(encoding="utf-8"))
    return [Bloque(b) for b in datos["bloques"]], datos["total"]


def subtitulos(bloques: list[Bloque], palabras_por_linea: int = 8, max_caracteres: int = 46) -> list[dict]:
    """Trocea la voz en cartelas legibles, cortando en la puntuación."""
    fuera = []
    for b in bloques:
        for linea in b.lineas:
            grupo: list[dict] = []
            for p in linea.palabras:
                grupo.append(p)
                texto = " ".join(x["p"] for x in grupo)
                cierra = p["p"].strip().endswith((".", "?", "!", "…"))
                respira = p["p"].strip().endswith((",", ":", ";")) and len(grupo) >= 4
                if cierra or respira or len(grupo) >= palabras_por_linea or len(texto) >= max_caracteres:
                    fuera.append(_cartela(b, linea, grupo))
                    grupo = []
            if grupo:
                fuera.append(_cartela(b, linea, grupo))
    return fuera


def _cartela(bloque: Bloque, linea: Linea, grupo: list[dict]) -> dict:
    t0 = bloque.inic + linea.inic + grupo[0]["t"]
    ultimo = grupo[-1]
    t1 = bloque.inic + linea.inic + ultimo["t"] + ultimo["d"]
    texto = " ".join(p["p"] for p in grupo)
    return {"b": bloque.id, "t0": t0, "t1": min(t1 + 0.35, bloque.fin), "texto": texto}


# ------------------------------------------------------------------- sfx ----
# (bloque, desplazamiento en s, efecto, ganancia)
SFX = [
    ("gancho", 0.02, "sub", 0.9),
    ("gancho", 0.55, "latido", 0.7),
    ("gancho", 1.25, "latido", 0.5),
    ("gancho", 2.35, "glitch", 0.7),
    ("gancho", 4.60, "whoosh", 0.55),
    ("gancho", 5.60, "latido", 0.45),
    ("golpe", 0.45, "golpe", 0.85),
    ("golpe", 2.10, "golpe", 0.7),
    ("golpe", 3.60, "golpe", 0.8),
    ("golpe", 5.10, "golpe", 0.95),
    ("golpe", 6.60, "whoosh", 0.5),
    ("revelacion", 0.00, "impacto", 1.0),
    ("revelacion", 0.05, "brillo", 0.7),
    ("revelacion", 1.70, "golpe", 0.55),
    ("revelacion", 3.90, "riser", 0.55),
    ("escritorio", 0.05, "whoosh", 0.7),
    ("escritorio", 1.10, "tecleo", 0.55),
    ("escritorio", 3.10, "check", 0.75),
    ("escritorio", 3.22, "check", 0.75),
    ("escritorio", 3.34, "check", 0.75),
    ("escritorio", 3.46, "check", 0.75),
    ("escritorio", 3.58, "check", 0.75),
    ("escritorio", 7.20, "clic", 0.8),
    ("escritorio", 7.40, "subida", 0.55),
    ("escritorio", 9.80, "campana", 0.8),
    ("escritorio", 11.10, "pop", 0.6),
    ("escritorio", 11.35, "pop", 0.6),
    ("escritorio", 11.60, "pop", 0.6),
    ("escritorio", 11.85, "pop", 0.6),
    ("escritorio", 12.10, "pop", 0.6),
    ("movil", 0.05, "whoosh", 0.7),
    ("movil", 1.30, "clic", 0.7),
    ("movil", 2.90, "clic", 0.7),
    ("movil", 4.30, "clic", 0.8),
    ("movil", 4.55, "subida", 0.5),
    ("movil", 7.40, "campana", 0.75),
    ("potencia", 0.05, "impacto", 0.75),
    ("potencia", 0.90, "golpe", 0.6),
    ("potencia", 2.70, "golpe", 0.6),
    ("potencia", 4.50, "golpe", 0.6),
    ("potencia", 6.60, "riser", 0.6),
    ("pago", 0.05, "whoosh", 0.7),
    ("pago", 1.30, "whoosh", 0.65),
    ("pago", 2.60, "whoosh", 0.7),
    ("pago", 3.90, "whoosh", 0.75),
    ("pago", 5.50, "impacto", 0.8),
    ("cierre", 0.10, "campana", 0.85),
    ("cierre", 0.80, "clic", 0.7),
    ("cierre", 2.40, "clic", 0.7),
    ("cierre", 5.20, "brillo", 0.6),
]


def lista_sfx(bloques: list[Bloque]) -> list[tuple[float, str, float]]:
    indice = {b.id: b for b in bloques}
    fuera = []
    for bloque, desplazamiento, nombre, ganancia in SFX:
        b = indice.get(bloque)
        if b is None or desplazamiento > b.dur:
            continue
        fuera.append((b.inic + desplazamiento, nombre, ganancia))
    return fuera


# --------------------------------------------------------------- dibujo -----
def texto(dib, xy, cadena, fnt, relleno, ancla="la", espaciado=0.0, alfa=255):
    """Texto con tracking opcional (PIL no lo trae)."""
    if not espaciado:
        dib.text(xy, cadena, font=fnt, fill=relleno + (alfa,) if len(relleno) == 3 else relleno, anchor=ancla)
        return
    x, y = xy
    total = sum(dib.textlength(c, font=fnt) + espaciado for c in cadena) - espaciado
    if ancla[0] == "m":
        x -= total / 2
    elif ancla[0] == "r":
        x -= total
    for c in cadena:
        dib.text((x, y), c, font=fnt, fill=relleno + (alfa,) if len(relleno) == 3 else relleno, anchor="l" + ancla[1])
        x += dib.textlength(c, font=fnt) + espaciado


def medir(dib, cadena, fnt, espaciado=0.0) -> float:
    return sum(dib.textlength(c, font=fnt) + espaciado for c in cadena) - (espaciado if cadena else 0)


def rrect(dib, caja, radio, relleno=None, borde=None, grosor=1):
    dib.rounded_rectangle(caja, radius=radio, fill=relleno, outline=borde, width=grosor)


def capa(tam) -> Image.Image:
    return Image.new("RGBA", tam, (0, 0, 0, 0))


def pegar(base: Image.Image, encima: Image.Image, xy, alfa: float = 1.0):
    if alfa <= 0:
        return
    if alfa < 1:
        encima = encima.copy()
        r, g, b, a = encima.split()
        a = a.point(lambda v: int(v * alfa))
        encima = Image.merge("RGBA", (r, g, b, a))
    base.alpha_composite(encima, (int(xy[0]), int(xy[1])))


def difuminar(im: Image.Image, radio: float) -> Image.Image:
    return im.filter(ImageFilter.GaussianBlur(radio))
