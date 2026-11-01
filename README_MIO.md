# Mi Suno

Descargador de playlists públicas de Suno con interfaz propia.

Construido sobre el núcleo MIT de
[zarigata/sudodownloader](https://github.com/zarigata/sudodownloader).

## Uso

Doble clic en **`Iniciar Mi Suno.bat`**.

1. Pega uno o más enlaces (`playlist` o `song`), uno por línea. También puedes
   arrastrarlos a la ventana o simplemente copiarlos: la app los detecta.
2. Pulsa **Analizar** (Ctrl+Enter). Verás la portada, las pistas y su duración.
3. Desmarca lo que no quieras, elige formato y carpeta.
4. Pulsa **Descargar**.

Durante la descarga puedes **Pausar** / **Reanudar** y **Detener**. Si algo
falla, aparece **Reintentar** y solo repite las pistas fallidas.

## Qué guarda

- Audio en `m4a` (original), `mp3`, `wav`, `flac` u `ogg`.
- Etiquetas: título, artista, álbum, fecha, nº de pista, género, comentario.
- Portada embebida y `cover.jpg` de la playlist.
- Letra embebida + `.txt` y `.lrc` al lado del audio.
- `.json` por pista, `_playlist.json` y `_playlist.m3u8` de la lista.
- `.mi_suno.json` como manifiesto: al repetir una descarga se salta lo que ya
  está y solo baja lo nuevo.

El MP3 por defecto requiere el `ffmpeg` moderno incluido en `herramientas\`.
Si no lo encuentra, guarda el `.m4a` original — válido, pero Windows Media
Player no reproduce Opus; usa VLC.

**WAV y FLAC no mejoran la calidad**: el origen ya es Opus con pérdida.

## Interfaz

PySide6 con **glassmorphism + bento grid** sobre tema oscuro cálido: ventana
sin marco, orbes difusos animados, tarjetas translúcidas, controles dibujados a
mano (toggle, stepper, segmentado, barra) y microanimaciones de 150–250 ms.

| Atajo | Acción |
|---|---|
| `Ctrl+Enter` | Analizar / Descargar |
| `Ctrl+O` | Elegir carpeta |
| `Ctrl+,` | Ajustes avanzados |
| `Ctrl+F` | Filtrar pistas |

Ajustes: proxy HTTP/SOCKS5, pausa entre pistas, concurrencia (1–3), reintentos,
timeout, notificaciones y cerrar a la bandeja. Se guardan con QSettings.
Historial en el icono del reloj. Log en `%APPDATA%\MiSuno\mi_suno.log`.

## Archivos

| Archivo | Qué es |
|---|---|
| `app_pyside.py` | Interfaz premium (PySide6) |
| `engine.py` | Motor de descarga sin UI |
| `mi_suno.py` | Interfaz clásica (tkinter), respaldo |
| `suno_dl.py` | Núcleo MIT original (CLI) |
| `herramientas/ffmpeg.exe` | ffmpeg 7.1 para convertir y etiquetar |
| `assets/mi_suno.svg` | Icono original (vectorial) |
| `assets/mi_suno.ico` | Icono multi-resolución para compilar |
| `build_icon.py` | Regenera el `.ico` desde el `.svg` |
| `compilar.bat` | Compila a `.exe` con PyInstaller |
| `instalador/` | Instalador `.msi` (WiX) con su arte y scripts |
| `ROADMAP.md` | Funciones: hechas y pendientes |

## Icono

El icono se genera desde `assets/mi_suno.svg` a un `.ico` con 7 tamaños
(16 a 256 px), válido para Windows y PyInstaller:

```
.venv\Scripts\python.exe build_icon.py
```

## Compilar

Ejecuta `compilar.bat`. El resultado queda en `dist\Mi Suno\Mi Suno.exe`
(la primera vez necesita internet para instalar PyInstaller).

## Instalador

Con `dist\Mi Suno` ya compilado, ejecuta `instalador\compilar_instalador.bat`.
Deja `instalador\Suno v1.msi`, que:

- instala en `C:\Program Files\Suno v1` (pide administrador, como cualquier programa);
- crea el acceso directo en el menú Inicio y aparece en *Aplicaciones instaladas*;
- se desinstala desde ahí, borrando también la carpeta.

El instalador reutiliza la paleta de la app (crema, ámbar `#F2A94E`, coral `#E8705B`).

| Archivo | Qué es |
|---|---|
| `instalador/Producto.wxs` | Definición del MSI (carpetas, acceso, pantallas) |
| `instalador/Ficheros.wxs` | Lista de archivos, generada automáticamente |
| `instalador/generar_componentes.py` | Regenera `Ficheros.wxs` desde `dist\Mi Suno` |
| `instalador/hacer_arte.py` | Genera `banner.bmp` y `fondo.bmp` de las pantallas |
| `instalador/arte/licencia.rtf` | Texto de la licencia que se muestra al instalar |
| `instalador/wix/` | WiX Toolset 3.14 (se descarga solo la primera vez) |

El primer paso del script descarga WiX; después ya funciona sin internet.

Durante la instalación aparece la pantalla **Accesos directos**, con dos casillas
marcadas por defecto: *En el menú Inicio* y *En el escritorio*. Se pueden
desmarcar, o cambiarlas por línea de comandos:

```
msiexec /i "Suno v1.msi" START_SHORTCUT=0 DESKTOP_SHORTCUT=0
```

## Actualizaciones

Entre el historial y los ajustes hay un botón con dos modos:

- **flechas circulares**: busca una versión nueva (gira mientras comprueba);
- **flecha hacia abajo**: aparece cuando hay una versión más reciente; al pulsarlo
  descarga el `.msi` en `Descargas`, abre el instalador y cierra la app.

La comprobación lee un JSON pequeño desde la URL del *canal de actualizaciones*
(se configura en Ajustes):

```json
{
  "version": "1.1.1",
  "url": "https://tu-servidor.com/Suno%20v1.msi"
}
```

Si `version` es mayor que `APP_VERSION` (en `app_pyside.py`), el botón cambia a
modo descarga. Un `version.json` estático en cualquier hosting (GitHub Pages,
un bucket, tu web) basta.

## Línea de comandos

```
.venv\Scripts\python.exe suno_dl.py "https://suno.com/playlist/ID"
```

## Licencia

Núcleo (`suno_dl.py`) MIT © zarigata — ver `LICENSE`.
Interfaz y motor propios: tuyos.

Solo para playlists públicas. Respeta los derechos de los autores.
