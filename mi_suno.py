#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mi Suno Downloader — versión propia con interfaz gráfica.

Se apoya en el núcleo MIT de "Suno Playlist Downloader" de zarigata
(https://github.com/zarigata/sudodownloader). Licencia MIT.

Sin cuenta, sin cuota, sin bloqueos de pago.
"""

from __future__ import annotations

import os
import queue
import random
import re
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import suno_dl as core

APP_NAME = "Mi Suno Downloader"
APP_VERSION = "1.1"

PROJECT_DIR = Path(__file__).resolve().parent

# ffmpeg debe ser moderno: los builds viejos (<2020) no decodifican Opus,
# que es el códec que Suno entrega dentro del .m4a.
MIN_FFMPEG_YEAR = 2020

# Carpeta propia primero; luego otras instalaciones conocidas.
FFMPEG_CANDIDATES = [
    PROJECT_DIR / "herramientas",
    Path(r"C:\Users\vejie\AppData\Local\Programs\SethSuno Studio Pro\herramientas"),
]


def _ffmpeg_year(folder: Path) -> int:
    exe = folder / "ffmpeg.exe"
    if not exe.exists():
        return 0
    try:
        out = subprocess.run(
            [str(exe), "-version"],
            capture_output=True,
            text=True,
            timeout=15,
            encoding="utf-8",
            errors="replace",
        ).stdout
    except Exception:  # noqa: BLE001
        return 0
    m = re.search(r"Copyright \(c\) 2000-(\d{4})", out or "")
    return int(m.group(1)) if m else 0


def locate_ffmpeg() -> str:
    """Devuelve una carpeta con un ffmpeg capaz de decodificar Opus, o ''."""
    for cand in FFMPEG_CANDIDATES:
        if _ffmpeg_year(cand) >= MIN_FFMPEG_YEAR:
            return str(cand)
    which = shutil.which("ffmpeg")
    if which:
        folder = Path(which).parent
        if _ffmpeg_year(folder) >= MIN_FFMPEG_YEAR:
            return str(folder)
    return ""


class _ConsoleShim:
    """Permite reutilizar convert_if_wanted(), que espera un Console de rich."""

    def __init__(self, log):
        self._log = log

    def print(self, *args, **kwargs):
        self._log(" ".join(str(a) for a in args))


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.q: queue.Queue = queue.Queue()
        self.worker: threading.Thread | None = None
        self.cancel = threading.Event()

        root.title(f"{APP_NAME} v{APP_VERSION}")
        root.geometry("720x640")
        root.minsize(640, 560)

        self._build_ui()
        self._poll_queue()

    # ------------------------------------------------------------------ UI --
    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}
        main = ttk.Frame(self.root)
        main.pack(fill="both", expand=True, **pad)

        ttk.Label(
            main,
            text="Pega uno o más enlaces públicos de playlist de Suno\n"
                 "(https://suno.com/playlist/…), uno por línea.",
            justify="left",
        ).pack(anchor="w")

        self.txt_urls = tk.Text(main, height=5, wrap="word", undo=True)
        self.txt_urls.pack(fill="x", pady=(4, 10))

        opts = ttk.LabelFrame(main, text="Opciones")
        opts.pack(fill="x", pady=(0, 10))

        row1 = ttk.Frame(opts)
        row1.pack(fill="x", padx=8, pady=6)
        ttk.Label(row1, text="Guardar en:").pack(side="left")
        self.var_out = tk.StringVar(
            value=str(Path.home() / "Music" / "Suno Downloads")
        )
        ttk.Entry(row1, textvariable=self.var_out).pack(
            side="left", fill="x", expand=True, padx=6
        )
        ttk.Button(row1, text="Elegir…", command=self._pick_dir).pack(side="left")

        row2 = ttk.Frame(opts)
        row2.pack(fill="x", padx=8, pady=6)
        self.var_mp3 = tk.BooleanVar(value=True)
        ttk.Checkbutton(row2, text="Convertir a MP3", variable=self.var_mp3).pack(
            side="left"
        )
        ttk.Label(row2, text="Pausa entre pistas (s):").pack(side="left", padx=(16, 4))
        self.var_delay = tk.DoubleVar(value=2.0)
        ttk.Spinbox(
            row2, from_=0, to=60, increment=1, width=5, textvariable=self.var_delay
        ).pack(side="left")

        row3 = ttk.Frame(opts)
        row3.pack(fill="x", padx=8, pady=6)
        ttk.Label(row3, text="Proxy/VPN (opcional):").pack(side="left")
        self.var_proxy = tk.StringVar()
        ttk.Entry(row3, textvariable=self.var_proxy).pack(
            side="left", fill="x", expand=True, padx=6
        )

        actions = ttk.Frame(main)
        actions.pack(fill="x", pady=(0, 8))
        self.btn_start = ttk.Button(actions, text="Descargar", command=self._start)
        self.btn_start.pack(side="left")
        self.btn_cancel = ttk.Button(
            actions, text="Detener", command=self._stop, state="disabled"
        )
        self.btn_cancel.pack(side="left", padx=8)

        self.pb = ttk.Progressbar(main, mode="determinate", maximum=100)
        self.pb.pack(fill="x", pady=(0, 4))
        self.var_status = tk.StringVar(value="Listo.")
        ttk.Label(main, textvariable=self.var_status).pack(anchor="w")

        self.log = tk.Text(main, height=14, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, pady=(8, 0))

    # ------------------------------------------------------------- helpers --
    def _pick_dir(self):
        d = filedialog.askdirectory(initialdir=self.var_out.get())
        if d:
            self.var_out.set(d)

    def _log(self, msg: str):
        self.q.put(("log", msg))

    def _set_status(self, msg: str):
        self.q.put(("status", msg))

    def _set_progress(self, pct: float | None):
        self.q.put(("progress", pct))

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "log":
                    self.log.configure(state="normal")
                    self.log.insert("end", payload + "\n")
                    self.log.see("end")
                    self.log.configure(state="disabled")
                elif kind == "status":
                    self.var_status.set(payload)
                elif kind == "progress":
                    if payload is None:
                        self.pb.configure(mode="indeterminate")
                        self.pb.start(60)
                    else:
                        self.pb.stop()
                        self.pb.configure(mode="determinate", value=payload)
                elif kind == "done":
                    self._finish(payload)
        except queue.Empty:
            pass
        self.root.after(80, self._poll_queue)

    # ------------------------------------------------------------- actions --
    def _start(self):
        raw = [ln.strip() for ln in self.txt_urls.get("1.0", "end").splitlines()]
        raw = [ln for ln in raw if ln]
        if not raw:
            messagebox.showwarning(APP_NAME, "Pega al menos un enlace de playlist.")
            return
        urls = []
        for ln in raw:
            try:
                urls.append(core.extract_playlist_id(ln))
            except ValueError:
                messagebox.showerror(APP_NAME, f"Enlace inválido:\n{ln}")
                return

        self.cancel.clear()
        self.btn_start.configure(state="disabled")
        self.btn_cancel.configure(state="normal")
        self._set_progress(0)
        self._log("=" * 50)
        self.worker = threading.Thread(
            target=self._run,
            args=(
                urls,
                self.var_out.get(),
                self.var_mp3.get(),
                max(0.0, self.var_delay.get()),
                self.var_proxy.get().strip(),
            ),
            daemon=True,
        )
        self.worker.start()

    def _stop(self):
        self.cancel.set()
        self._set_status("Deteniendo tras la pista actual…")

    def _finish(self, code):
        self.btn_start.configure(state="normal")
        self.btn_cancel.configure(state="disabled")
        self.pb.stop()
        self.pb.configure(mode="determinate", value=0 if code else 100)
        self._set_status("Listo." if code == 0 else "Terminado con avisos.")

    # -------------------------------------------------------------- worker --
    def _run(self, pids, outdir, want_mp3, delay, proxy):
        try:
            code = self._download_all(pids, outdir, want_mp3, delay, proxy)
        except Exception as e:  # noqa: BLE001 — mostrar cualquier fallo al usuario
            self._log(f"ERROR: {e}")
            code = 1
        self.q.put(("done", code))

    def _download_all(self, pids, outdir, want_mp3, delay, proxy) -> int:
        ff_dir = locate_ffmpeg()
        if ff_dir and ff_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = ff_dir + os.pathsep + os.environ.get("PATH", "")

        session = core.make_session(proxy)
        if want_mp3:
            if not core.find_ffmpeg():
                self._log(
                    "AVISO: no hay un ffmpeg moderno. Se guardará .m4a (Opus), "
                    "que Windows Media Player no reproduce. Instala ffmpeg o deja "
                    "herramientas\\ffmpeg.exe en la carpeta."
                )
                want_mp3 = False
            else:
                self._log("ffmpeg OK: se convertirá a MP3 (compatible con todo).")

        console = _ConsoleShim(self._log)
        code = 0
        for n, pid in enumerate(pids):
            if self.cancel.is_set():
                break
            if n:
                self._log("— siguiente playlist —")
            code = max(code, self._one(pid, session, outdir, want_mp3, delay, proxy, console))
        return code

    def _one(self, pid, session, outdir, want_mp3, delay, proxy, console) -> int:
        self._set_status("Obteniendo información de la playlist…")
        self._set_progress(None)
        try:
            meta = core.fetch_playlist(session, pid)
        except core.PlaylistNotFoundError:
            self._log(f"Playlist no encontrada o no pública: {pid}")
            return 1
        except core.BlockedError:
            self._log("Suno rechazó la conexión (403/429). Espera un rato o usa un proxy.")
            return 2

        clips = meta.get("clips") or []
        name = core.sanitize_filename(meta.get("name") or pid)
        if not clips:
            self._log(f"'{name}' está vacía.")
            return 0

        dest_dir = Path(outdir) / name
        dest_dir.mkdir(parents=True, exist_ok=True)
        self._log(f"[{name}] {len(clips)} pistas → {dest_dir}")

        referer = f"https://suno.com/playlist/{pid}"
        width = len(str(len(clips)))
        total = len(clips)
        done_count = 0

        for i, clip in enumerate(clips, 1):
            if self.cancel.is_set():
                self._log("Detenido por el usuario.")
                return 1
            title = (clip.get("title") or clip.get("id") or "sin título").strip()
            num = str(i).zfill(width)
            url, ext = core.pick_media(clip)
            if not url:
                self._log(f"  ⚠ {num} — {title}: sin audio disponible")
                done_count += 1
                continue

            dest = dest_dir / f"{num} - {core.sanitize_filename(title)}{ext}"
            mp3_dest = dest.with_suffix(".mp3")

            if want_mp3 and mp3_dest.exists():
                self._log(f"  · {num} — {title}: ya existe (mp3)")
                done_count += 1
                continue
            if dest.exists() and core.is_playable_audio(dest):
                self._log(f"  · {num} — {title}: ya existe")
                if want_mp3:
                    self._convert(dest, console)
                done_count += 1
                continue

            self._set_status(f"Descargando {num}/{total}: {title}")
            try:
                self._fetch_file(session, url, dest, referer, i, total)
                rights = core.fetch_rights(session, clip.get("id"))
                blob = dest.read_bytes()
                dest.write_bytes(core.decrypt_bytes(blob, clip.get("id"), rights))
                if not core.is_playable_audio(dest):
                    raise RuntimeError("archivo descifrado inválido")
                final = self._convert(dest, console) if want_mp3 else dest
                size = core.human_size(final.stat().st_size)
                self._log(f"  ✓ {num} — {title} ({size})")
            except core.BlockedError:
                self._log("Suno pidió reducir velocidad (403/429). Deteniendo.")
                return 2
            except Exception as e:  # noqa: BLE001
                self._log(f"  ✗ {num} — {title}: {e}")

            done_count += 1
            self._set_progress(done_count / total * 100)
            if i < total and not self.cancel.is_set():
                time.sleep(delay + random.uniform(0, delay))

        self._log(f"Terminado: {name}")
        return 0

    def _convert(self, dest: Path, console) -> Path:
        out, _ = core.convert_if_wanted(dest, True, dest.stem, console)
        return out

    def _fetch_file(self, session, url, dest: Path, referer, idx, total):
        tmp = dest.with_suffix(dest.suffix + ".part")
        with session.get(
            url, headers={"Referer": referer}, stream=True, timeout=(15, 60)
        ) as r:
            if r.status_code in (403, 429):
                raise core.BlockedError(f"HTTP {r.status_code}")
            r.raise_for_status()
            length = int(r.headers.get("Content-Length") or 0) or None
            written = 0
            with open(tmp, "wb") as fh:
                for chunk in r.iter_content(64 * 1024):
                    if self.cancel.is_set():
                        raise RuntimeError("cancelado")
                    if chunk:
                        fh.write(chunk)
                        written += len(chunk)
                        if length:
                            frac = (idx - 1 + written / length) / total
                            self._set_progress(frac * 100)
        tmp.replace(dest)


def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
