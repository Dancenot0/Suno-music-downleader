#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convierte la carpeta compilada (dist\\Mi Suno) en un fragmento WiX con todos
los archivos, para que el .msi los instale tal cual.

    .venv\\Scripts\\python.exe instalador\\generar_componentes.py
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIST = RAIZ / "dist" / "Mi Suno"
SALIDA = Path(__file__).resolve().parent / "Ficheros.wxs"

ESPACIO = uuid.UUID("6f2b3a4c-7d51-4a2e-9a10-3c8b1e5d7f20")


def esc(texto: str) -> str:
    return (
        texto.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


class Nodo:
    def __init__(self, nombre: str, ruta: Path):
        self.nombre = nombre
        self.ruta = ruta
        self.hijos: dict[str, "Nodo"] = {}
        self.archivos: list[Path] = []


def recorrer() -> Nodo:
    raiz = Nodo("", DIST)
    for archivo in sorted(DIST.rglob("*")):
        if archivo.is_dir():
            continue
        rel = archivo.relative_to(DIST)
        nodo = raiz
        for parte in rel.parts[:-1]:
            nodo = nodo.hijos.setdefault(parte, Nodo(parte, nodo.ruta / parte))
        nodo.archivos.append(archivo)
    return raiz


def main() -> int:
    if not DIST.exists():
        print(f"No existe {DIST}. Compila app_pyside.py antes.")
        return 1

    raiz = recorrer()
    lineas: list[str] = []
    refs: list[str] = []
    dirs = 0
    comps = 0

    def emitir(nodo: Nodo) -> None:
        nonlocal dirs, comps
        for archivo in nodo.archivos:
            comps += 1
            cid = f"c_{comps:04d}"
            fid = f"f_{comps:04d}"
            refs.append(cid)
            guid = str(uuid.uuid5(ESPACIO, archivo.relative_to(DIST).as_posix())).upper()
            src = esc(str(archivo))
            lineas.append(
                f'      <Component Id="{cid}" Guid="{{{guid}}}" Win64="yes">\n'
                f'        <File Id="{fid}" Source="{src}" KeyPath="yes" />\n'
                f"      </Component>"
            )
        for nombre, hijo in sorted(nodo.hijos.items()):
            dirs += 1
            did = f"d_{dirs:04d}"
            lineas.append(f'      <Directory Id="{did}" Name="{esc(nombre)}">')
            emitir(hijo)
            lineas.append("      </Directory>")

    emitir(raiz)

    partes = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">',
        "  <Fragment>",
        '    <DirectoryRef Id="INSTALLFOLDER">',
        *lineas,
        "    </DirectoryRef>",
        "  </Fragment>",
        "",
        "  <Fragment>",
        '    <ComponentGroup Id="Ficheros">',
        *[f'      <ComponentRef Id="{r}" />' for r in refs],
        "    </ComponentGroup>",
        "  </Fragment>",
        "</Wix>",
        "",
    ]

    SALIDA.write_text("\n".join(partes), encoding="utf-8")
    print(f"{comps} archivos, {dirs} carpetas -> {SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
