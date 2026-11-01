# Suno v1

Descargador de playlists públicas de Suno para Windows, con interfaz propia.

> **Web oficial:** <https://dancenot0.github.io/Suno-music-downleader/>

Pega el enlace de una playlist pública, elige formato y descarga. Cada archivo
sale con carátula, letra y etiquetas **dentro del propio audio**, así que la
carpeta de descargas se queda limpia: solo música.

---

## Qué incluye

- **Formatos:** MP3 (VBR o CBR), M4A original, WAV, FLAC y OGG.
- **Vista previa** de la playlist con portada, duración y selección por pistas.
- **Pausa y reanudación**, reintento solo de lo que falló y manifiesto para no
  volver a bajar lo que ya tienes.
- **Metadatos completos**: título, artista, álbum, género, portada y letra dentro
  del archivo. Los archivos sueltos (`.json`, `.lrc`, `.txt`, `cover.jpg`, `.m3u8`)
  son opcionales y están apagados por defecto.
- **Carpeta limpia**: el registro de lo ya descargado vive en
  `%APPDATA%\MiSuno\manifiestos`, no entre tus canciones.
- **Proxy** HTTP y SOCKS5, concurrencia limitada y pausas humanas.
- **Actualizaciones** desde la propia app (un botón, dos modos: buscar y descargar).
- **Instalador `.msi`** que crea accesos en el menú Inicio y en el escritorio.

## Instalar

Descarga el instalador desde la [web oficial](https://dancenot0.github.io/Suno-music-downleader/)
—un solo archivo, sin compilar nada— o directamente desde
[`descargas/Suno-v1.msi`](descargas/Suno-v1.msi).

Instala en `C:\Program Files\Suno v1` y pide permisos de administrador, como
cualquier programa.

Requisitos: Windows 10 u 11 de 64 bits. No hace falta cuenta de Suno ni Python.

## Compilar desde el código

```bat
Iniciar Mi Suno.bat        :: entorno y dependencias
compilar.bat               :: genera dist\Mi Suno\Mi Suno.exe
instalador\compilar_instalador.bat   :: genera el .msi
```

La captura que aparece en la web se genera desde la app real:

```bat
.venv\Scripts\python.exe captura_web.py
```

Escribe `assets\app-v1.webp` (y un `.png` de reserva). Vuelve a ejecutarlo si
cambias la interfaz, para que la web no muestre una versión antigua.

El instalador necesita `herramientas\ffmpeg.exe`, que **no se versiona** por su
tamaño (83 MB): descarga una compilación de <https://ffmpeg.org/download.html> y
déjala en esa carpeta antes de compilar.

## Actualizaciones

Al abrir la app se consulta el canal **en silencio**: si ya estás al día no dice
nada; solo avisa cuando hay una versión nueva (y entonces el botón cambia a
flecha de descarga). Se puede desactivar con «Buscar actualizaciones al iniciar»
en Ajustes. El botón de la barra superior sigue estando para buscarlas a mano.

La app consulta un JSON pequeño:

```json
{
  "version": "1.1.0",
  "url": "https://dancenot0.github.io/Suno-music-downleader/descargas/Suno-v1.msi"
}
```

El canal público está en `version.json`, servido por GitHub Pages:
<https://dancenot0.github.io/Suno-music-downleader/version.json>

Para publicar una versión nueva:

1. Compila con `compilar.bat` y `instalador\compilar_instalador.bat`.
2. Copia el `.msi` sobre `descargas\Suno-v1.msi` (mismo nombre, se sustituye).
3. Actualiza `version` en `version.json`, `VERSION` en `app.js` y
   `APP_VERSION` en `app_pyside.py`.
4. `git add -A && git commit -m "v1.1.1" && git push`.

El botón de actualizar de las apps ya instaladas verá el cambio y ofrecerá la
descarga sola.

> **Ojo con el tamaño:** cada versión deja el `.msi` anterior en el historial
> de git (≈72 MB por versión). Para dos o tres versiones no es problema; si el
> proyecto crece, lo limpio es mover las versiones antiguas a *Releases* y dejar
> en `descargas/` solo la última.

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
