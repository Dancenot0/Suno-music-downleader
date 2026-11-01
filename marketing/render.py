# -*- coding: utf-8 -*-
"""Render del promo: sirve marketing/, pinta la página en Chrome headless
frame a frame y lo entrega a ffmpeg. Todo local, sin captura de pantalla.

  python marketing/render.py                 # video completo
  python marketing/render.py --foto 23.4     # una sola foto para revisar
  python marketing/render.py --desde 0 --hasta 6 --salida prueba.mp4
"""
from __future__ import annotations

import argparse
import base64
import http.server
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from functools import partial
from pathlib import Path

import websocket

RAIZ = Path(__file__).resolve().parent
PROYECTO = RAIZ.parent
FFMPEG = PROYECTO / "herramientas" / "ffmpeg.exe"
CHROME = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
PERFIL = Path(os.environ.get("TEMP", str(RAIZ))) / "suno-chrome-promo"

ANCHO, ALTO, FPS = 1920, 1080, 30


def puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Servidor(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def arrancar_servidor(puerto: int):
    manejador = partial(Servidor, directory=str(PROYECTO))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", puerto), manejador)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def arrancar_chrome(puerto_cdp: int) -> subprocess.Popen:
    PERFIL.mkdir(parents=True, exist_ok=True)
    orden = [
        str(CHROME),
        "--headless=new",
        f"--remote-debugging-port={puerto_cdp}",
        f"--user-data-dir={PERFIL}",
        f"--window-size={ANCHO},{ALTO}",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        "--disable-background-timer-throttling",
        "--disable-renderer-backgrounding",
        "--disable-backgrounding-occluded-windows",
        "--disable-features=Translate,BackForwardCache",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-infobars",
        "--mute-audio",
        "--allow-file-access-from-files",
        "about:blank",
    ]
    return subprocess.Popen(orden, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def esperar_cdp(puerto: int, limite: float = 25.0) -> dict:
    fin = time.time() + limite
    while time.time() < fin:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/json/version", timeout=1) as r:
                return json.loads(r.read())
        except Exception:
            time.sleep(0.25)
    raise RuntimeError("Chrome no abrió el puerto de depuración")


class CDP:
    def __init__(self, ws_url: str):
        self.ws = websocket.create_connection(ws_url, timeout=120, max_size=None)
        self.id = 0

    def enviar(self, metodo: str, **params):
        self.id += 1
        propio = self.id
        self.ws.send(json.dumps({"id": propio, "method": metodo, "params": params}))
        while True:
            mensaje = json.loads(self.ws.recv())
            if mensaje.get("id") == propio:
                if "error" in mensaje:
                    raise RuntimeError(f"{metodo}: {mensaje['error']}")
                return mensaje.get("result", {})

    def evaluar(self, expresion: str, await_promise: bool = False):
        r = self.enviar(
            "Runtime.evaluate",
            expression=expresion,
            returnByValue=True,
            awaitPromise=await_promise,
        )
        return r.get("result", {}).get("value")

    def foto(self, formato: str = "png") -> bytes:
        if formato == "jpeg":
            r = self.enviar(
                "Page.captureScreenshot",
                format="jpeg", quality=96,
                captureBeyondViewport=False,
                fromSurface=True,
                optimizeForSpeed=True,
            )
        else:
            r = self.enviar(
                "Page.captureScreenshot",
                format="png",
                captureBeyondViewport=False,
                fromSurface=True,
                optimizeForSpeed=True,
            )
        return base64.b64decode(r["data"])


def abrir_pagina(cdp: CDP, url: str) -> None:
    cdp.enviar("Page.enable")
    cdp.enviar("Runtime.enable")
    cdp.enviar(
        "Emulation.setDeviceMetricsOverride",
        width=ANCHO, height=ALTO, deviceScaleFactor=1, mobile=False,
    )
    cdp.enviar("Page.navigate", url=url)
    fin = time.time() + 60
    while time.time() < fin:
        if cdp.evaluar("document.body.dataset.listo === '1'"):
            break
        time.sleep(0.2)
    else:
        raise RuntimeError("la página no terminó de cargar")
    # deja que las imágenes y las fuentes se asienten
    cdp.evaluar("document.fonts.ready.then(()=>1)", await_promise=True)
    time.sleep(0.4)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--foto", type=str, help="fotogramas sueltos, separados por comas (segundos)")
    ap.add_argument("--desde", type=float, default=0.0)
    ap.add_argument("--hasta", type=float, default=None)
    ap.add_argument("--salida", default="video/promo.mp4")
    ap.add_argument("--crf", default="16")
    ap.add_argument("--formato", default="jpeg", choices=["jpeg", "png"])
    ap.add_argument("--sin-espera", action="store_true",
                    help="no espera dos frames del navegador (más rápido, revisar antes)")
    ap.add_argument("--sin-audio", action="store_true")
    args = ap.parse_args()

    datos = json.loads((RAIZ / "audio" / "timeline.json").read_text(encoding="utf-8"))
    total = datos["total"]

    puerto_web = puerto_libre()
    puerto_cdp = puerto_libre()
    arrancar_servidor(puerto_web)
    chrome = arrancar_chrome(puerto_cdp)
    try:
        esperar_cdp(puerto_cdp)
        with urllib.request.urlopen(f"http://127.0.0.1:{puerto_cdp}/json/list") as r:
            objetivos = json.loads(r.read())
        pagina = next(o for o in objetivos if o["type"] == "page")
        cdp = CDP(pagina["webSocketDebuggerUrl"])
        url = f"http://127.0.0.1:{puerto_web}/marketing/promo.html"
        abrir_pagina(cdp, url)
        if args.sin_espera:
            cdp.evaluar("window.SIN_RAF = true")

        if args.foto is not None:
            for marca in args.foto.split(","):
                t = float(marca)
                cdp.evaluar(f"window.pintar({t})", await_promise=True)
                destino = RAIZ / "video" / f"foto-{t:05.2f}.png"
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_bytes(cdp.foto())
                print(f"foto en {destino}")
            return 0

        desde = args.desde
        hasta = args.hasta if args.hasta is not None else total
        n_frames = int(round((hasta - desde) * FPS))
        destino = RAIZ / args.salida
        destino.parent.mkdir(parents=True, exist_ok=True)

        orden = [
            str(FFMPEG), "-y", "-loglevel", "error",
            "-f", "image2pipe", "-framerate", str(FPS),
            "-c:v", "mjpeg" if args.formato == "jpeg" else "png",
            "-i", "-",
            # el JPEG llega en rango completo: se pasa a rango de video (16-235)
            "-vf", "scale=in_range=full:out_range=tv:flags=bicubic,format=yuv420p",
            "-c:v", "libx264", "-preset", "slow", "-crf", args.crf,
            "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2",
            "-color_range", "tv", "-colorspace", "bt709",
            "-color_primaries", "bt709", "-color_trc", "bt709",
            "-movflags", "+faststart", str(destino),
        ]
        ff = subprocess.Popen(orden, stdin=subprocess.PIPE)

        inicio = time.time()
        for i in range(n_frames):
            t = desde + i / FPS
            cdp.evaluar(f"window.pintar({t:.5f})", await_promise=True)
            ff.stdin.write(cdp.foto(args.formato))
            if i % 90 == 0:
                avance = (i + 1) / n_frames * 100
                transcurrido = time.time() - inicio
                eta = transcurrido / max(1, i + 1) * (n_frames - i - 1)
                print(
                    f"  {avance:5.1f}%  frame {i}/{n_frames}  "
                    f"{transcurrido:6.0f}s  (faltan {eta:5.0f}s)",
                    flush=True,
                )
        ff.stdin.close()
        codigo = ff.wait()
        if codigo != 0:
            raise RuntimeError(f"ffmpeg terminó con {codigo}")

        if not args.sin_audio:
            mezcla = RAIZ / "audio" / "mezcla.wav"
            if mezcla.exists():
                con_audio = destino.with_name(destino.stem + "-con-audio.mp4")
                subprocess.run(
                    [
                        str(FFMPEG), "-y", "-loglevel", "error",
                        "-i", str(destino), "-i", str(mezcla),
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "224k",
                        "-shortest", "-movflags", "+faststart", str(con_audio),
                    ],
                    check=True,
                )
                print(f"con audio: {con_audio}")

        print(f"listo: {destino}  ({time.time() - inicio:.0f}s)")
        return 0
    finally:
        chrome.terminate()
        try:
            chrome.wait(timeout=10)
        except Exception:
            chrome.kill()


if __name__ == "__main__":
    sys.exit(main())
