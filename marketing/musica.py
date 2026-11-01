# -*- coding: utf-8 -*-
"""Banda sonora y efectos, sintetizados con numpy (sin samples de terceros).

Uso:  python marketing/musica.py
Salida: marketing/audio/mezcla.wav  (48 kHz, estéreo, 16 bit)
"""
from __future__ import annotations

import math
import wave
from pathlib import Path

import numpy as np

from comun import Bloque, cargar_timeline, lista_sfx

SR = 48000
RAIZ = Path(__file__).resolve().parent
AUDIO = RAIZ / "audio"

BPM = 92.0
NEGRA = 60.0 / BPM
COMPAS = NEGRA * 4

# Am - F - C - G  (i - VI - III - VII)
ACORDES = [
    dict(bajo=55.00, notas=[220.00, 261.63, 329.63]),   # Am
    dict(bajo=43.65, notas=[174.61, 220.00, 261.63]),   # F
    dict(bajo=65.41, notas=[261.63, 329.63, 392.00]),   # C
    dict(bajo=49.00, notas=[196.00, 246.94, 293.66]),   # G
]


def segundos(n: float) -> int:
    return int(round(n * SR))


def ruido(n: int, rng: np.random.Generator) -> np.ndarray:
    return rng.standard_normal(n).astype(np.float32)


def suavizar(x: np.ndarray, ancho: int) -> np.ndarray:
    """Paso bajo barato: media móvil por sumas acumuladas (O(n))."""
    if ancho <= 1:
        return x
    ancho = int(ancho)
    nucleo = np.ones(ancho, dtype=np.float32) / ancho
    if ancho <= 64:
        return np.convolve(x, nucleo, mode="same").astype(np.float32)
    acumulado = np.cumsum(np.pad(x.astype(np.float64), (ancho, ancho), mode="edge"))
    ventana = acumulado[2 * ancho :] - acumulado[: -2 * ancho]
    return (ventana / ancho).astype(np.float32)[: len(x)]


def envolver(x: np.ndarray, ataque: float, caida: float, total: float) -> np.ndarray:
    n = len(x)
    a = max(1, segundos(ataque))
    d = max(1, segundos(caida))
    env = np.ones(n, dtype=np.float32)
    a = min(a, n)
    env[:a] = np.linspace(0, 1, a) ** 1.6
    if d < n:
        env[-d:] *= np.linspace(1, 0, d) ** 1.5
    return x * env


def exp_decae(n: int, tau: float) -> np.ndarray:
    return np.exp(-np.arange(n, dtype=np.float32) / (SR * tau))


# ------------------------------------------------------------- instrumentos -
def golpe_bombo(freq0=150.0, freq1=44.0, dur=0.55, rng=None) -> np.ndarray:
    n = segundos(dur)
    t = np.arange(n, dtype=np.float32) / SR
    f = freq0 * np.exp(-t * 26) + freq1
    fase = np.cumsum(2 * np.pi * f / SR)
    cuerpo = np.sin(fase) * np.exp(-t * 7.5)
    clic = np.zeros(n, dtype=np.float32)
    if rng is not None:
        c = ruido(segundos(0.012), rng) * 0.25
        clic[: len(c)] = c * np.linspace(1, 0, len(c))
    return (cuerpo + clic).astype(np.float32)


def nota_pad(freq: float, dur: float, rng: np.random.Generator) -> np.ndarray:
    n = segundos(dur)
    t = np.arange(n, dtype=np.float32) / SR
    vibrato = 1 + 0.0016 * np.sin(2 * np.pi * 0.23 * t + rng.random() * 6)
    x = np.zeros(n, dtype=np.float32)
    for det, peso in ((-0.0012, 0.5), (0.0, 1.0), (0.0014, 0.5)):
        f = freq * (1 + det) * vibrato
        fase = 2 * np.pi * np.cumsum(f) / SR
        x += peso * (np.sin(fase) + 0.22 * np.sin(2 * fase) + 0.07 * np.sin(3 * fase))
    x = suavizar(x, 9)
    env = np.ones(n, dtype=np.float32)
    r = min(segundos(0.55), n - 1)
    env[:r] = np.linspace(0, 1, r) ** 2
    s = min(segundos(0.9), n - r)
    env[-s:] *= np.linspace(1, 0, s) ** 1.4
    return (x * env / 2.1).astype(np.float32)


def nota_campana(freq: float, dur=1.4, fuerza=1.0, rng=None) -> np.ndarray:
    n = segundos(dur)
    t = np.arange(n, dtype=np.float32) / SR
    x = (
        np.sin(2 * np.pi * freq * t) * np.exp(-t * 3.4)
        + 0.42 * np.sin(2 * np.pi * freq * 2.76 * t) * np.exp(-t * 6.0)
        + 0.18 * np.sin(2 * np.pi * freq * 5.4 * t) * np.exp(-t * 9.0)
    )
    return (x * fuerza * 0.35).astype(np.float32)


def nota_bajo(freq: float, dur: float) -> np.ndarray:
    n = segundos(dur)
    t = np.arange(n, dtype=np.float32) / SR
    x = np.sin(2 * np.pi * freq * t) + 0.28 * np.sin(2 * np.pi * freq * 2 * t)
    env = np.ones(n, dtype=np.float32)
    a = min(segundos(0.02), n - 1)
    env[:a] = np.linspace(0, 1, a)
    d = min(segundos(0.12), n - a)
    env[-d:] *= np.linspace(1, 0, d)
    return (x * env).astype(np.float32)


def charles(dur=0.09, rng=None) -> np.ndarray:
    n = segundos(dur)
    x = ruido(n, rng)
    x = np.diff(x, prepend=0.0)  # paso alto
    return (x * exp_decae(n, 0.028) * 0.16).astype(np.float32)


# ------------------------------------------------------------------- mezcla -
class Pista:
    def __init__(self, total: int):
        self.izq = np.zeros(total, dtype=np.float32)
        self.der = np.zeros(total, dtype=np.float32)

    def suma(self, inicio: float, x: np.ndarray, ganancia: float = 1.0, pan: float = 0.0):
        i = segundos(inicio)
        if i >= len(self.izq):
            return
        n = min(len(x), len(self.izq) - i)
        if n <= 0:
            return
        gi = ganancia * math.sqrt(0.5 * (1 - pan))
        gd = ganancia * math.sqrt(0.5 * (1 + pan))
        self.izq[i : i + n] += x[:n] * gi
        self.der[i : i + n] += x[:n] * gd


def seccion(b: Bloque, nombre: str) -> bool:
    return b.id == nombre


def construir_musica(bloques: list[Bloque], total: float) -> Pista:
    n_total = segundos(total + 1.0)
    rng = np.random.default_rng(7)
    mezcla = Pista(n_total)

    rev = next(b for b in bloques if b.id == "revelacion")
    esc = next(b for b in bloques if b.id == "escritorio")
    pot = next(b for b in bloques if b.id == "potencia")
    pag = next(b for b in bloques if b.id == "pago")
    cie = next(b for b in bloques if b.id == "cierre")

    # --- colchón armónico desde la revelación hasta el cierre --------------
    import time as _tmp
    _t0 = _tmp.perf_counter()
    t = rev.inic
    compas = 0
    while t < cie.inic + 1.2:
        import time as _t
        _a = _t.perf_counter()
        acorde = ACORDES[compas % 4]
        dur = COMPAS * 1.02
        for k, f in enumerate(acorde["notas"]):
            pan = (-0.35, 0.0, 0.35)[k]
            mezcla.suma(t, nota_pad(f, dur, rng), 0.16, pan)
            mezcla.suma(t, nota_pad(f * 2, dur, rng), 0.05, -pan * 0.6)
        t += COMPAS
        compas += 1

    # --- drone de entrada (tensión) ---------------------------------------
    t = 0.0
    while t < rev.inic - 0.05:
        dur = min(3.0, rev.inic - t + 0.15)
        x = nota_pad(110.0, dur, rng) * 0.5 + nota_pad(55.0, dur, rng) * 0.35
        mezcla.suma(t, x, 0.20, 0.0)
        t += 2.9

    # --- ritmo ------------------------------------------------------------
    t = esc.inic
    compas = 0
    while t < cie.inic:
        tramo = (
            "groove" if t < pot.inic
            else "lift" if t < pag.inic
            else "climax"
        )
        fuerza = {"groove": 1.0, "lift": 1.08, "climax": 1.2}[tramo]
        acorde = ACORDES[compas % 4]

        for pulso in (0.0, 2.0):
            mezcla.suma(t + pulso * NEGRA, golpe_bombo(rng=rng), 0.52 * fuerza, 0.0)
        # bombo suave a contratiempo cada dos compases
        if compas % 2 == 1:
            mezcla.suma(t + 3.5 * NEGRA, golpe_bombo(120, 46, 0.35, rng), 0.18 * fuerza, 0.0)

        # bajo en corcheas con silencio en el 4º pulso
        for i, paso in enumerate((0, 3, 6)):
            dur = NEGRA * (1.4 if paso != 6 else 1.0)
            mezcla.suma(t + paso * NEGRA / 2, nota_bajo(acorde["bajo"], dur), 0.30 * fuerza, 0.0)

        # arpegio de campanas en corcheas
        patron = [0, 2, 1, 2, 0, 1, 2, 1]
        for i, idx in enumerate(patron):
            f = acorde["notas"][idx] * 2
            if f > 1200:
                f /= 2
            pan = -0.45 if i % 2 == 0 else 0.45
            fuerza_nota = 0.75 if i in (0, 4) else 0.5
            mezcla.suma(
                t + i * NEGRA / 2,
                nota_campana(f, 1.1, fuerza_nota * 0.55, rng),
                0.115 * fuerza,
                pan,
            )

        # charles a contratiempo
        for i in (1, 3, 5, 7):
            mezcla.suma(t + i * NEGRA / 2, charles(rng=rng), 0.5 * fuerza, 0.25)

        t += COMPAS
        compas += 1

    # --- outro: acorde final y campanas lejanas ----------------------------
    for k, f in enumerate([220.0, 261.63, 329.63, 440.0]):
        mezcla.suma(cie.inic + 0.15, nota_pad(f, 7.5, rng), 0.13, (-0.4, 0.35, -0.1, 0.4)[k])
    for i, paso in enumerate((0.0, 1.3, 2.6, 4.0)):
        mezcla.suma(cie.inic + 0.4 + paso, nota_campana(880 / (1.0 + 0.12 * i), 2.2, 0.5, rng), 0.10, 0.3 * (-1) ** i)

    # --- vinilo ------------------------------------------------------------
    ruido_lp = suavizar(ruido(n_total, rng), 5)
    mezcla.izq += ruido_lp * 0.0035
    mezcla.der += ruido_lp * 0.0033

    # --- aire (reverb barata por reflexiones) ------------------------------
    for retardo, g in ((0.041, 0.30), (0.067, 0.22), (0.103, 0.16), (0.149, 0.10)):
        d = segundos(retardo)
        mezcla.izq[d:] += mezcla.izq[:-d] * g
        mezcla.der[d:] += mezcla.der[:-d] * g * 0.94

    # --- automatización de secciones ---------------------------------------
    def ganancia_por_tramo(arranque: float, fin: float, ganancia: float, rampa=0.35):
        a = segundos(max(0.0, arranque - rampa))
        b = segundos(arranque + rampa)
        c = segundos(max(0.0, fin - rampa))
        d = segundos(fin + rampa)
        g = np.zeros(n_total, dtype=np.float32)
        g[a:b] = np.linspace(0, 1, max(1, b - a))
        g[b:c] = 1
        g[c:d] = np.linspace(1, 0, max(1, d - c))
        return (1 - ganancia) + ganancia * g

    # la música baja en la intro y sube en la revelación
    curva = np.ones(n_total, dtype=np.float32)
    curva *= ganancia_por_tramo(0.0, rev.inic, 0.0, 0.6)
    mezcla.izq *= curva
    mezcla.der *= curva

    # --- efectos ------------------------------------------------------------
    for cuando, nombre, ganancia in lista_sfx(bloques):
        x, pan = efecto(nombre, rng)
        mezcla.suma(cuando, x, ganancia * 0.55, pan)

    return mezcla


# --------------------------------------------------------------------- sfx --
def efecto(nombre: str, rng: np.random.Generator) -> tuple[np.ndarray, float]:
    if nombre == "sub":
        n = segundos(1.8)
        t = np.arange(n) / SR
        f = 70 * np.exp(-t * 2.2) + 28
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.9)
        return (x * 0.9).astype(np.float32), 0.0

    if nombre == "latido":
        n = segundos(0.5)
        t = np.arange(n) / SR
        x = np.sin(2 * np.pi * 48 * t) * np.exp(-t * 12)
        return (x * 0.8).astype(np.float32), 0.0

    if nombre == "golpe":
        x = golpe_bombo(120, 42, 0.6, rng) * 0.9
        cola = np.zeros(segundos(0.5), dtype=np.float32)
        x = np.concatenate([x, cola])
        return (x * 0.75).astype(np.float32), 0.0

    if nombre == "impacto":
        n = segundos(2.6)
        t = np.arange(n) / SR
        f = 90 * np.exp(-t * 6) + 33
        cuerpo = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.6)
        aire = suavizar(ruido(n, rng), 40) * np.exp(-t * 3.2) * 0.5
        return ((cuerpo + aire) * 0.85).astype(np.float32), 0.0

    if nombre == "whoosh":
        n = segundos(0.85)
        t = np.arange(n) / SR
        x = ruido(n, rng)
        x = suavizar(x, 25)
        env = np.sin(np.pi * np.clip(t / 0.85, 0, 1)) ** 2
        return (x * env * 0.55).astype(np.float32), float(rng.uniform(-0.5, 0.5))

    if nombre == "riser":
        n = segundos(2.2)
        t = np.arange(n) / SR
        x = ruido(n, rng)
        ancho = (np.linspace(40, 3, n)).astype(int)
        trozos = np.convolve(x, np.ones(9) / 9, mode="same")
        env = (t / 2.2) ** 2.2
        tono = np.sin(2 * np.pi * np.cumsum(np.linspace(180, 900, n)) / SR) * 0.25
        return ((trozos * 0.7 + tono) * env).astype(np.float32), 0.0

    if nombre == "tecleo":
        n = segundos(1.5)
        x = np.zeros(n, dtype=np.float32)
        for k in range(14):
            i = segundos(0.03 + k * 0.095)
            c = ruido(segundos(0.02), rng) * np.linspace(1, 0, segundos(0.02))
            x[i : i + len(c)] += c * 0.3
        return x, -0.15

    if nombre == "clic":
        n = segundos(0.09)
        t = np.arange(n) / SR
        x = np.sin(2 * np.pi * 1250 * t) * np.exp(-t * 90)
        return (x * 0.5).astype(np.float32), 0.1

    if nombre == "check":
        n = segundos(0.22)
        t = np.arange(n) / SR
        x = (
            np.sin(2 * np.pi * 880 * t) * np.exp(-t * 40)
            + 0.6 * np.sin(2 * np.pi * 1320 * t) * np.exp(-t * 30)
        )
        return (x * 0.35).astype(np.float32), 0.25

    if nombre == "pop":
        n = segundos(0.28)
        t = np.arange(n) / SR
        f = 520 * np.exp(-t * 12) + 170
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 16)
        return (x * 0.5).astype(np.float32), float(rng.uniform(-0.6, 0.6))

    if nombre == "campana":
        n = segundos(3.0)
        t = np.arange(n) / SR
        x = (
            np.sin(2 * np.pi * 1046 * t) * np.exp(-t * 2.4)
            + 0.5 * np.sin(2 * np.pi * 1568 * t) * np.exp(-t * 3.0)
            + 0.3 * np.sin(2 * np.pi * 2093 * t) * np.exp(-t * 4.5)
        )
        return (x * 0.3).astype(np.float32), 0.2

    if nombre == "glitch":
        n = segundos(0.35)
        x = ruido(n, rng) * 0.35
        paso = segundos(0.015)
        for i in range(0, n, paso * 2):
            x[i : i + paso] *= 0.15
        return x.astype(np.float32), 0.0

    if nombre == "subida":
        n = segundos(2.4)
        t = np.arange(n) / SR
        f = np.linspace(220, 660, n)
        x = np.sin(2 * np.pi * np.cumsum(f) / SR)
        return (x * (t / 2.4) * 0.16).astype(np.float32), 0.0

    if nombre == "brillo":
        n = segundos(2.4)
        t = np.arange(n) / SR
        x = np.zeros(n, dtype=np.float32)
        for f in (1568.0, 2093.0, 2637.0):
            x += np.sin(2 * np.pi * f * t) * np.exp(-t * 2.2) * 0.25
        return x.astype(np.float32), 0.0

    return np.zeros(segundos(0.1), dtype=np.float32), 0.0


# ------------------------------------------------------------------- montaje -
def montar_voz(bloques: list[Bloque], n_total: int) -> np.ndarray:
    pista = np.zeros((2, n_total), dtype=np.float32)
    for b in bloques:
        for linea in b.lineas:
            with wave.open(str(linea.wav), "rb") as w:
                canales = w.getnchannels()
                datos = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
            datos = datos.astype(np.float32) / 32768.0
            if canales == 2:
                datos = datos.reshape(-1, 2).mean(axis=1)
            i = segundos(b.inic + linea.inic)
            n = min(len(datos), n_total - i)
            pista[0, i : i + n] += datos[:n]
            pista[1, i : i + n] += datos[:n]
    return pista


def escribir(ruta: Path, izq: np.ndarray, der: np.ndarray) -> None:
    datos = np.stack([izq, der], axis=1)
    datos = np.clip(datos, -1, 1)
    pcm = (datos * 32767).astype(np.int16)
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def main() -> None:
    bloques, total = cargar_timeline()
    n_total = segundos(total)

    musica = construir_musica(bloques, total)
    musica.izq = musica.izq[:n_total]
    musica.der = musica.der[:n_total]

    voz = montar_voz(bloques, n_total)

    # ducking: la música baja mientras habla
    envoltura = np.sqrt(voz[0] ** 2 + voz[1] ** 2)
    envoltura = suavizar(envoltura, segundos(0.10))
    envoltura = np.clip(envoltura * 5.0, 0, 1)
    suave = suavizar(envoltura, segundos(0.09))
    duck = 1.0 - 0.42 * suave

    mezcla_izq = musica.izq * 0.55 * duck + voz[0] * 1.05
    mezcla_der = musica.der * 0.55 * duck + voz[1] * 1.05

    # fundido final
    f = segundos(1.2)
    mezcla_izq[-f:] *= np.linspace(1, 0, f) ** 1.2
    mezcla_der[-f:] *= np.linspace(1, 0, f) ** 1.2

    pico = max(np.abs(mezcla_izq).max(), np.abs(mezcla_der).max())
    if pico > 0:
        ganancia = 0.92 / pico
        mezcla_izq *= ganancia
        mezcla_der *= ganancia

    escribir(AUDIO / "mezcla.wav", mezcla_izq, mezcla_der)
    print(f"mezcla.wav listo · {total:.2f} s · pico normalizado")


if __name__ == "__main__":
    main()
