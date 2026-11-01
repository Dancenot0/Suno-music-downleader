#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Motor de descarga de Mi Suno.

Funciones: vista previa, selección de pistas, canción individual, formatos
(m4a/mp3/wav/flac/ogg), etiquetas, portada, letras, sidecar JSON, manifiesto,
normalización, video, pausa/reanudación, concurrencia, proxy y registro.

Núcleo MIT © zarigata — https://github.com/zarigata/sudodownloader
"""

from __future__ import annotations

import base64
import json
import os
import random
import re
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import requests

import suno_dl as core

try:
    import mutagen
    from mutagen.flac import FLAC, Picture
    from mutagen.id3 import (
        APIC,
        COMM,
        TALB,
        TCON,
        TDRC,
        TIT2,
        TPE1,
        TRCK,
        TXXX,
        USLT,
        ID3,
    )
    from mutagen.mp4 import MP4, MP4Cover
    from mutagen.oggopus import OggOpus
    from mutagen.oggvorbis import OggVorbis

    MUTAGEN = True
except Exception:  # noqa: BLE001
    MUTAGEN = False

PROJECT_DIR = Path(__file__).resolve().parent
APP_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "MiSuno"
APP_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = APP_DIR / "mi_suno.log"
HISTORY_PATH = APP_DIR / "history.json"

MIN_FFMPEG_YEAR = 2020
FFMPEG_CANDIDATES = [
    PROJECT_DIR / "herramientas",
    Path(r"C:\Users\vejie\AppData\Local\Programs\SethSuno Studio Pro\herramientas"),
]

API_CLIP = "https://studio-api.prod.suno.com/api/clip/{cid}"

EXT = {"m4a": ".m4a", "mp3": ".mp3", "wav": ".wav", "flac": ".flac", "ogg": ".ogg"}

QUALITIES = {
    "vbr0": ("VBR q0 · máxima", ["-q:a", "0"]),
    "vbr2": ("VBR q2 · alta", ["-q:a", "2"]),
    "vbr4": ("VBR q4 · media", ["-q:a", "4"]),
    "cbr320": ("320 kbps", ["-b:a", "320k"]),
    "cbr256": ("256 kbps", ["-b:a", "256k"]),
    "cbr192": ("192 kbps", ["-b:a", "192k"]),
    "cbr128": ("128 kbps", ["-b:a", "128k"]),
}


# ------------------------------------------------------------------ modelos --
@dataclass
class Track:
    id: str
    index: int
    title: str
    duration: float = 0.0
    model: str = ""
    tags: str = ""
    created: str = ""
    cover: str = ""
    video: str = ""
    lyrics: str = ""
    raw: dict = field(default_factory=dict)


@dataclass
class Playlist:
    id: str
    name: str
    kind: str = "playlist"
    author: str = ""
    handle: str = ""
    cover: str = ""
    description: str = ""
    total_duration: float = 0.0
    tracks: list[Track] = field(default_factory=list)


@dataclass
class Options:
    outdir: str
    fmt: str = "mp3"
    quality: str = "vbr2"
    tags: bool = True
    cover: bool = True
    lyrics: bool = True
    sidecar: bool = True
    cover_file: bool = True
    playlist_files: bool = True
    template: str = "{n} - {title}"
    normalize: bool = False
    video: bool = False
    overwrite: bool = False
    delay: float = 2.0
    concurrency: int = 1
    proxy: str = ""
    timeout: int = 60
    retries: int = 3


@dataclass
class Callbacks:
    log: Callable[[str], None] = lambda m: None
    status: Callable[[str], None] = lambda m: None
    progress: Callable[[float], None] = lambda p: None
    track: Callable[[str, float, float], None] = lambda t, p, s: None
    done: Callable[[dict], None] = lambda r: None


# ------------------------------------------------------------------ utilidad --
def _ffmpeg_year(folder: Path) -> int:
    exe = folder / "ffmpeg.exe"
    if not exe.exists():
        return 0
    try:
        out = subprocess.run(
            [str(exe), "-version"],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
        ).stdout
    except Exception:  # noqa: BLE001
        return 0
    m = re.search(r"Copyright \(c\) 2000-(\d{4})", out or "")
    return int(m.group(1)) if m else 0


def locate_ffmpeg() -> str:
    for cand in FFMPEG_CANDIDATES:
        if _ffmpeg_year(cand) >= MIN_FFMPEG_YEAR:
            return str(cand)
    which = shutil.which("ffmpeg")
    if which:
        folder = Path(which).parent
        if _ffmpeg_year(folder) >= MIN_FFMPEG_YEAR:
            return str(folder)
    return ""


def ffmpeg_exe() -> str:
    folder = locate_ffmpeg()
    return str(Path(folder) / "ffmpeg.exe") if folder else "ffmpeg"


def extract_target(text: str) -> tuple[str, str]:
    """Devuelve ('playlist'|'song', id) desde un enlace o id."""
    text = text.strip()
    m = re.search(r"suno\.com/(playlist|song)/([0-9a-fA-F-]{30,40})", text)
    if m:
        return ("playlist" if m.group(1) == "playlist" else "song", m.group(2).strip("/? "))
    if re.fullmatch(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        text,
    ):
        return ("playlist", text.lower())
    raise ValueError("no es un enlace de Suno")


def sanitize(name: str) -> str:
    return core.sanitize_filename(name)


def human_size(n: float) -> str:
    return core.human_size(int(n))


def log_to_file(msg: str) -> None:
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {msg}\n")
    except OSError:
        pass


def read_history() -> list:
    try:
        return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []


def push_history(pl: Playlist) -> None:
    items = [h for h in read_history() if h.get("id") != pl.id]
    items.insert(0, {
        "id": pl.id, "name": pl.name, "author": pl.author,
        "cover": pl.cover, "count": len(pl.tracks),
        "kind": pl.kind, "date": time.strftime("%Y-%m-%dT%H:%M:%S"),
    })
    try:
        HISTORY_PATH.write_text(
            json.dumps(items[:30], ensure_ascii=False, indent=1), encoding="utf-8"
        )
    except OSError:
        pass


def _session(proxy: str, timeout: int) -> requests.Session:
    s = core.make_session(proxy)
    s.request_timeout = timeout  # type: ignore[attr-defined]
    return s


# ---------------------------------------------------------------- preview --
def _track_from_clip(clip: dict, index: int) -> Track:
    md = clip.get("metadata") or {}
    dur = md.get("duration") or clip.get("duration") or 0
    try:
        dur = float(dur)
    except (TypeError, ValueError):
        dur = 0.0
    return Track(
        id=clip.get("id") or "",
        index=index,
        title=(clip.get("title") or "sin título").strip(),
        duration=dur,
        model=clip.get("major_model_version") or clip.get("model_name") or "",
        tags=clip.get("display_tags") or md.get("tags") or "",
        created=(clip.get("created_at") or "")[:10],
        cover=clip.get("image_large_url") or clip.get("image_url") or "",
        video=clip.get("video_url") or "",
        lyrics=md.get("prompt") or "",
        raw=clip,
    )


def preview(target: str, proxy: str = "", timeout: int = 60) -> Playlist:
    kind, ident = extract_target(target)
    s = _session(proxy, timeout)
    if kind == "song":
        r = s.get(API_CLIP.format(cid=ident), headers={"Referer": "https://suno.com"}, timeout=timeout)
        if r.status_code == 404:
            raise core.PlaylistNotFoundError(ident)
        r.raise_for_status()
        clip = r.json()
        tr = _track_from_clip(clip, 1)
        return Playlist(
            id=ident, name=tr.title, kind="song", author=clip.get("display_name") or "",
            handle=clip.get("handle") or "", cover=tr.cover, tracks=[tr],
            total_duration=tr.duration,
        )

    meta = core.fetch_playlist(s, ident)
    clips = meta.get("clips") or []
    tracks = [_track_from_clip(c, i) for i, c in enumerate(clips, 1)]
    return Playlist(
        id=ident,
        name=sanitize(meta.get("name") or ident),
        kind="playlist",
        author=(meta.get("user_display_name") or "").strip(),
        handle=(meta.get("user_handle") or "").strip(),
        cover=meta.get("image_url") or "",
        description=(meta.get("description") or "").strip(),
        total_duration=float(meta.get("total_duration") or 0),
        tracks=tracks,
    )


# ------------------------------------------------------------------- motor --
class Engine:
    def __init__(self, options: Options, callbacks: Callbacks):
        self.o = options
        self.cb = callbacks
        self.cancel = threading.Event()
        self.paused = threading.Event()
        self._lock = threading.Lock()
        self._ffmpeg = locate_ffmpeg()
        self._done = 0
        self._ok = 0
        self._partial: dict[str, float] = {}
        self._total = 0
        self._failed: list[str] = []
        self._skipped = 0
        self._folders: list[str] = []
        self.blocked = False

    # ------------------------------------------------------------ público --
    def pause(self):
        self.paused.set()
        self.cb.status("En pausa.")

    def resume(self):
        self.paused.clear()
        self.cb.status("Reanudando…")

    def run(self, playlists: list[Playlist], selection: dict[str, set[str]]) -> dict:
        if self._ffmpeg:
            os.environ["PATH"] = self._ffmpeg + os.pathsep + os.environ.get("PATH", "")
        if self.o.fmt != "m4a" and not self._ffmpeg:
            self.cb.log("ffmpeg no encontrado: se guardará .m4a original.")
            self.o.fmt = "m4a"

        jobs = []
        for pl in playlists:
            chosen = selection.get(pl.id)
            tracks = [t for t in pl.tracks if chosen is None or t.id in chosen]
            if tracks:
                jobs.append((pl, tracks))

        self._total = sum(len(t) for _, t in jobs)
        if not self._total:
            self.cb.log("No hay pistas seleccionadas.")
            return self._result(1)

        self.cb.log(
            f"{len(jobs)} playlist(s) · {self._total} pista(s) · "
            f"formato {self.o.fmt.upper()}"
        )

        for pl, tracks in jobs:
            if self.cancel.is_set():
                break
            self._download_playlist(pl, tracks)

        return self._result(0 if not self._failed else 1)

    # ------------------------------------------------------------ interno --
    def _result(self, code: int) -> dict:
        res = {
            "code": 2 if self.cancel.is_set() else code,
            "ok": self._ok,
            "skipped": self._skipped,
            "failed": list(self._failed),
            "folders": list(self._folders),
            "blocked": self.blocked,
            "cancelled": self.cancel.is_set(),
        }
        self.cb.done(res)
        return res

    def _wait_if_paused(self):
        while self.paused.is_set() and not self.cancel.is_set():
            time.sleep(0.2)

    def _report(self, tid: str, frac: float):
        with self._lock:
            self._partial[tid] = max(0.0, min(1.0, frac))
            overall = (self._done + sum(self._partial.values())) / max(1, self._total) * 100
        self.cb.progress(overall)

    def _emit_overall(self):
        with self._lock:
            overall = (self._done + sum(self._partial.values())) / max(1, self._total) * 100
        self.cb.progress(overall)

    def _download_playlist(self, pl: Playlist, tracks: list[Track]):
        dest_dir = Path(self.o.outdir)
        if pl.kind == "playlist":
            dest_dir = dest_dir / sanitize(pl.name)
        dest_dir.mkdir(parents=True, exist_ok=True)
        self._folders.append(str(dest_dir))

        manifest_path = dest_dir / ".mi_suno.json"
        manifest = self._load_manifest(manifest_path)

        cover_bytes = None
        if (self.o.cover or self.o.cover_file) and pl.cover:
            cover_bytes = self._fetch_cover(pl.cover)
            if cover_bytes and self.o.cover_file:
                try:
                    (dest_dir / "cover.jpg").write_bytes(cover_bytes)
                except OSError:
                    pass

        self.cb.status(f"{pl.name} · {len(tracks)} pista(s)")
        self.cb.log(f"[{pl.name}] {len(tracks)} pistas → {dest_dir}")

        if self.o.concurrency > 1 and len(tracks) > 1:
            with ThreadPoolExecutor(max_workers=min(3, self.o.concurrency)) as pool:
                futures = [
                    pool.submit(self._one, pl, t, dest_dir, cover_bytes, manifest, manifest_path)
                    for t in tracks
                ]
                for f in futures:
                    if self.cancel.is_set():
                        break
                    try:
                        f.result()
                    except Exception as e:  # noqa: BLE001
                        self.cb.log(f"  ✗ error inesperado: {e}")
        else:
            for t in tracks:
                if self.cancel.is_set():
                    break
                self._one(pl, t, dest_dir, cover_bytes, manifest, manifest_path)
                if not self.cancel.is_set():
                    time.sleep(self.o.delay + random.uniform(0, self.o.delay))

        if self.o.playlist_files:
            self._write_playlist_files(pl, tracks, dest_dir)

    def _one(self, pl, t: Track, dest_dir: Path, cover, manifest, manifest_path):
        if self.cancel.is_set():
            return
        self._wait_if_paused()
        if self.cancel.is_set():
            return

        num = str(t.index).zfill(len(str(max(1, len(pl.tracks)))))
        base = self._filename(t, num, pl)
        ext = EXT.get(self.o.fmt, ".m4a")
        dest = dest_dir / f"{base}{ext}"

        prev = manifest.get(t.id)
        already = False
        if prev and prev.get("fmt") == self.o.fmt:
            already = (dest_dir / prev.get("file", "")).exists()
        if dest.exists():
            already = True
        if already and not self.o.overwrite:
            self._skipped += 1
            existing = dest if dest.exists() else dest_dir / prev.get("file", "")
            self._finish_track(t.id, existing, t, "ya existe")
            return

        try:
            url, src_ext = core.pick_media(t.raw)
            is_video = False
            if self.o.video and t.video:
                url, src_ext, is_video = t.video, ".mp4", True
            if not url:
                raise RuntimeError("sin audio disponible")

            self.cb.status(f"{t.title}")
            raw = dest_dir / f".{t.id}{src_ext}.part"
            self._fetch(url, raw, t, pl)

            if is_video:
                raw.replace(dest_dir / f"{base}.mp4")
                manifest[t.id] = {"file": f"{base}.mp4", "fmt": "mp4", "date": t.created}
                self._save_manifest(manifest_path, manifest)
                self._finish_track(t.id, dest_dir / f"{base}.mp4", t, "video")
                return

            rights = core.fetch_rights(_session(self.o.proxy, self.o.timeout), t.id)
            raw.write_bytes(core.decrypt_bytes(raw.read_bytes(), t.id, rights))

            final = self._convert(raw, dest_dir, base, t)
            raw.unlink(missing_ok=True)

            if MUTAGEN:
                self._tag(final, t, pl, cover)

            if self.o.lyrics and t.lyrics:
                self._write_lyrics(final, t)

            if self.o.sidecar:
                self._write_sidecar(final, t, pl)

            manifest[t.id] = {"file": final.name, "fmt": self.o.fmt, "date": t.created}
            self._save_manifest(manifest_path, manifest)
            self._finish_track(t.id, final, t, "ok")
        except core.BlockedError:
            self.blocked = True
            self.cb.log("Suno pidió reducir velocidad (403/429). Deteniendo.")
            self.cancel.set()
        except Exception as e:  # noqa: BLE001
            if self.cancel.is_set():
                return
            self._failed.append(t.id)
            self.cb.log(f"  ✗ {t.title}: {e}")
            with self._lock:
                self._done += 1
                self._partial.pop(t.id, None)
            self._emit_overall()

    def _finish_track(self, tid, path: Path, t: Track, label: str):
        with self._lock:
            self._done += 1
            self._ok += 1
            self._partial.pop(tid, None)
        try:
            size = human_size(path.stat().st_size)
        except OSError:
            size = "?"
        self.cb.log(f"  ✓ {t.title} ({size})")
        self._report(tid, 0.0)

    def _filename(self, t: Track, num: str, pl: Playlist) -> str:
        fields = {
            "n": num,
            "title": t.title,
            "artist": pl.author or t.raw.get("display_name") or "Suno",
            "album": pl.name,
            "date": t.created,
            "model": t.model,
        }
        name = self.o.template or "{n} - {title}"
        for k, v in fields.items():
            name = name.replace("{" + k + "}", str(v or ""))
        return sanitize(name)

    def _fetch(self, url: str, dest: Path, t: Track, pl: Playlist):
        session = _session(self.o.proxy, self.o.timeout)
        referer = f"https://suno.com/playlist/{pl.id}" if pl.kind == "playlist" else "https://suno.com"
        last = None
        for attempt in range(max(1, self.o.retries)):
            try:
                with session.get(url, headers={"Referer": referer}, stream=True,
                                 timeout=(15, self.o.timeout)) as r:
                    if r.status_code in (403, 429):
                        raise core.BlockedError(f"HTTP {r.status_code}")
                    r.raise_for_status()
                    length = int(r.headers.get("Content-Length") or 0) or 0
                    written = 0
                    start = time.time()
                    with open(dest, "wb") as fh:
                        for chunk in r.iter_content(64 * 1024):
                            self._wait_if_paused()
                            if self.cancel.is_set():
                                raise RuntimeError("cancelado")
                            if chunk:
                                fh.write(chunk)
                                written += len(chunk)
                                frac = written / length if length else 0.0
                                speed = written / max(0.001, time.time() - start)
                                self._report(t.id, frac * 0.9)
                                self.cb.track(t.title, frac * 100, speed)
                return
            except core.BlockedError:
                raise
            except Exception as e:  # noqa: BLE001
                last = e
                if attempt < self.o.retries - 1:
                    time.sleep(5 * (attempt + 1))
        raise RuntimeError(f"descarga fallida: {last}")

    def _convert(self, src: Path, dest_dir: Path, base: str, t: Track) -> Path:
        fmt = self.o.fmt
        ext = EXT.get(fmt, ".m4a")
        dst = dest_dir / f"{base}{ext}"

        if fmt == "m4a" and not self.o.normalize and src.suffix.lower() == ".m4a":
            if dst.exists():
                dst.unlink()
            src.replace(dst)
            return dst

        if not self._ffmpeg:
            if dst.exists():
                dst.unlink()
            src.replace(dst)
            return dst

        args = [ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(src), "-map_metadata", "-1"]
        if self.o.normalize:
            args += ["-af", "loudnorm=I=-16:TP=-1.5:LRA=11"]
        if fmt == "mp3":
            args += ["-c:a", "libmp3lame"] + QUALITIES.get(self.o.quality, QUALITIES["vbr2"])[1]
        elif fmt == "wav":
            args += ["-c:a", "pcm_s16le"]
        elif fmt == "flac":
            args += ["-c:a", "flac"]
        elif fmt == "ogg":
            args += ["-c:a", "libopus", "-b:a", "160k"]
        elif fmt == "m4a":
            args += ["-c:a", "aac", "-b:a", "192k"]
        args += [str(dst)]

        proc = subprocess.run(args, capture_output=True)
        if proc.returncode != 0 or not dst.exists():
            raise RuntimeError(proc.stderr.decode(errors="replace").strip()[:200] or "ffmpeg falló")
        return dst

    def _tag(self, path: Path, t: Track, pl: Playlist, cover: bytes | None):
        try:
            artist = pl.author or t.raw.get("display_name") or "Suno"
            album = pl.name
            genre = t.tags
            title = t.title
            date = t.created
            track_no = str(t.index)
            comment = f"Generado con Suno · modelo {t.model}".strip()
            suffix = path.suffix.lower()

            if suffix == ".mp3":
                tags = ID3()
                tags.add(TIT2(encoding=3, text=title))
                tags.add(TPE1(encoding=3, text=artist))
                tags.add(TALB(encoding=3, text=album))
                tags.add(TDRC(encoding=3, text=date))
                tags.add(TRCK(encoding=3, text=track_no))
                if genre:
                    tags.add(TCON(encoding=3, text=genre))
                tags.add(COMM(encoding=3, lang="spa", desc="", text=comment))
                tags.add(TXXX(encoding=3, desc="Suno", text=t.id))
                if t.lyrics:
                    tags.add(USLT(encoding=3, lang="spa", desc="", text=t.lyrics))
                if cover:
                    tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=cover))
                tags.save(path)

            elif suffix == ".m4a":
                audio = MP4(path)
                audio["\xa9nam"] = [title]
                audio["\xa9ART"] = [artist]
                audio["\xa9alb"] = [album]
                audio["\xa9day"] = [date]
                audio["trkn"] = [(t.index, 0)]
                if genre:
                    audio["\xa9gen"] = [genre]
                audio["\xa9cmt"] = [comment]
                if t.lyrics:
                    audio["\xa9lyr"] = [t.lyrics]
                if cover:
                    audio["covr"] = [MP4Cover(cover, imageformat=MP4Cover.FORMAT_JPEG)]
                audio.save()

            elif suffix == ".flac":
                audio = FLAC(path)
                audio["title"] = title
                audio["artist"] = artist
                audio["album"] = album
                audio["date"] = date
                audio["tracknumber"] = track_no
                if genre:
                    audio["genre"] = genre
                audio["comment"] = comment
                if t.lyrics:
                    audio["lyrics"] = t.lyrics
                if cover:
                    pic = Picture()
                    pic.type = 3
                    pic.mime = "image/jpeg"
                    pic.data = cover
                    audio.add_picture(pic)
                audio.save()

            elif suffix == ".ogg":
                try:
                    audio = OggOpus(path)
                except Exception:  # noqa: BLE001
                    audio = OggVorbis(path)
                audio["title"] = title
                audio["artist"] = artist
                audio["album"] = album
                audio["date"] = date
                audio["tracknumber"] = track_no
                if genre:
                    audio["genre"] = genre
                audio["comment"] = comment
                if t.lyrics:
                    audio["lyrics"] = t.lyrics
                if cover:
                    pic = Picture()
                    pic.type = 3
                    pic.mime = "image/jpeg"
                    pic.data = cover
                    audio["metadata_block_picture"] = [
                        base64.b64encode(pic.write()).decode("ascii")
                    ]
                audio.save()
        except Exception as e:  # noqa: BLE001
            self.cb.log(f"  · etiquetas no aplicadas a {t.title}: {e}")

    def _write_lyrics(self, media: Path, t: Track):
        base = media.with_suffix("")
        text = t.lyrics.strip()
        try:
            (base.with_suffix(base.suffix + ".txt")).write_text(text, encoding="utf-8")
            lrc = f"[ti:{t.title}]\n[ar:]\n[al:]\n\n{text}\n"
            (base.with_suffix(base.suffix + ".lrc")).write_text(lrc, encoding="utf-8")
        except OSError:
            pass

    def _write_sidecar(self, media: Path, t: Track, pl: Playlist):
        data = {
            "id": t.id,
            "title": t.title,
            "artist": pl.author,
            "album": pl.name,
            "playlist_id": pl.id,
            "duration": t.duration,
            "model": t.model,
            "tags": t.tags,
            "created": t.created,
            "cover": t.cover,
            "video": t.video,
            "lyrics": t.lyrics,
            "file": media.name,
        }
        try:
            media.with_suffix(media.suffix + ".json").write_text(
                json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8"
            )
        except OSError:
            pass

    def _write_playlist_files(self, pl: Playlist, tracks: list[Track], dest_dir: Path):
        try:
            info = {
                "id": pl.id, "name": pl.name, "author": pl.author,
                "handle": pl.handle, "description": pl.description,
                "cover": pl.cover, "total_duration": pl.total_duration,
                "tracks": [
                    {"index": t.index, "id": t.id, "title": t.title,
                     "duration": t.duration, "model": t.model, "tags": t.tags}
                    for t in tracks
                ],
            }
            (dest_dir / "_playlist.json").write_text(
                json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8"
            )
            m3u = ["#EXTM3U"]
            for t in tracks:
                m3u.append(f"#EXTINF:{int(t.duration)},{pl.author} - {t.title}")
                num = str(t.index).zfill(len(str(max(1, len(pl.tracks)))))
                base = self._filename(t, num, pl)
                m3u.append(f"{base}{EXT.get(self.o.fmt, '.m4a')}")
            (dest_dir / "_playlist.m3u8").write_text("\n".join(m3u), encoding="utf-8")
        except OSError:
            pass

    def _fetch_cover(self, url: str) -> bytes | None:
        try:
            r = _session(self.o.proxy, self.o.timeout).get(url, timeout=self.o.timeout)
            if r.status_code == 200:
                return r.content
        except Exception:  # noqa: BLE001
            pass
        return None

    @staticmethod
    def _load_manifest(path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {}

    def _save_manifest(self, path: Path, manifest: dict):
        with self._lock:
            try:
                path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
            except OSError:
                pass
