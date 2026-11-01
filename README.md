# Suno v1

Descargador de playlists públicas de Suno para Windows, con interfaz propia.

> **Web oficial:** <https://dancenot0.github.io/Suno-music-downleader/>

Pega el enlace de una playlist pública, elige formato y descarga. Cada archivo
sale con carátula incrustada, letra (`.lrc` y `.txt`), etiquetas y un `.json` con
todos los datos que expone Suno.

---

## Qué incluye

- **Formatos:** MP3 (VBR o CBR), M4A original, WAV, FLAC y OGG.
- **Vista previa** de la playlist con portada, duración y selección por pistas.
- **Pausa y reanudación**, reintento solo de lo que falló y manifiesto para no
  volver a bajar lo que ya tienes.
- **Metadatos completos**: título, artista, álbum, género, portada y letra.
- **Proxy** HTTP y SOCKS5, concurrencia limitada y pausas humanas.
- **Actualizaciones** desde la propia app (un botón, dos modos: buscar y descargar).
- **Instalador `.msi`** que crea accesos en el menú Inicio y en el escritorio.

## Instalar

Descarga el instalador desde la [página de versiones](https://github.com/Dancenot0/Suno-music-downleader/releases/latest)
o desde la web oficial. Instala en `C:\Program Files\Suno v1` y pide permisos de
administrador, como cualquier programa.

Requisitos: Windows 10 u 11 de 64 bits. No hace falta cuenta de Suno ni Python.

## Compilar desde el código

```bat
Iniciar Mi Suno.bat        :: entorno y dependencias
compilar.bat               :: genera dist\Mi Suno\Mi Suno.exe
instalador\compilar_instalador.bat   :: genera el .msi
```

El instalador necesita `herramientas\ffmpeg.exe`, que **no se versiona** por su
tamaño (83 MB): descarga una compilación de <https://ffmpeg.org/download.html> y
déjala en esa carpeta antes de compilar.

## Actualizaciones

La app consulta un JSON pequeño:

```json
{
  "version": "1.1.0",
  "url": "https://github.com/Dancenot0/Suno-music-downleader/releases/latest/download/Suno-v1.msi"
}
```

El canal público está en `docs/version.json`, servido por GitHub Pages:
<https://dancenot0.github.io/Suno-music-downleader/version.json>

Para publicar una versión nueva: sube la Release con el archivo llamado
`Suno-v1.msi`, actualiza `version` en `docs/version.json` y `APP_VERSION` en
`app_pyside.py`.

## Licencia

- **Suno v1** (interfaz, motor propio, instalador, web): gratis para usar, **no**
  para modificar ni redistribuir. Ver [`LICENCIA.md`](LICENCIA.md).
- **Núcleo `suno_dl.py`**: MIT © [zarigata](https://github.com/zarigata/sudodownloader),
  con su licencia intacta en [`LICENSE`](LICENSE).
- Créditos de todos los componentes en [`TERCEROS.md`](TERCEROS.md).

## Aviso

Solo playlists **públicas**. Nada de cuentas privadas ni de saltarse límites de
Suno. Respeta los derechos de los autores y los términos del servicio.
El proyecto no está afiliado a Suno.
