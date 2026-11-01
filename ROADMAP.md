# Roadmap — Mi Suno

Lista completa de funciones para exprimir la app. Basada en lo que **realmente
expone la API pública** de Suno (verificado) y en lo que ofrecen las mejores
herramientas del mercado (SunoHelper, Suno Tracks Exporter, Duckmartians
Suno-Downloader, Undetectr).

Estado: `[x]` hecho · `[~]` parcial · `[ ]` pendiente
Esfuerzo: **S** (horas) · **M** (1–2 días) · **L** (3+ días)

> Última pasada: implementado todo el Sprint 1 y casi todo el Sprint 2.
> Lo que queda está marcado `[ ]` y explicado al final.

---

## 0. Lo que la API permite (verificado)

- Playlist pública: nombre, descripción, portada, autor, nº pistas, duración total.
- Por pista: título, fecha, `metadata.tags` (estilo), `metadata.prompt` (letra
  completa con etiquetas de estructura), `metadata.duration`, portada
  (`image_url`, `image_large_url`), modelo (`model_name`, `major_model_version`),
  `display_tags`, reproducciones, `video_url` (cuando existe), `has_stem`.
- Audio real en `media_urls` → **m4a con Opus**. (`audio_url` devuelve `forbidden`.)
- Endpoint de **pista suelta** `/api/clip/{id}` → 200. Permite enlaces
  `suno.com/song/{id}`.
- **No** hay URL pública de stems (requiere cuenta). **No** se accede a
  bibliotecas privadas.

---

## 1. Formatos y conversión

- [x] **Selector de formato**: original `.m4a`, MP3, WAV, FLAC, OGG/Opus. — S
- [x] **Calidad MP3**: VBR q0/q2/q4 o CBR 128/192/256/320. — S
- [x] Convertir a MP3 con `libmp3lame`. — S
- [x] **Normalización de volumen** EBU R128 (`loudnorm`). — M
- [ ] **Fade in/out** y recorte de silencio al inicio/fin. — M
- [x] **Conversión en paralelo** (hasta 3 pistas a la vez). — M
- [x] Metadatos propios escritos después de convertir (`-map_metadata -1`). — S
- [ ] **Validación real** del audio con `ffprobe` (duración/códec). — S
- [ ] Reparar/reintentar archivos corruptos automáticamente. — S
- [x] Nota honesta en la UI: WAV/FLAC no recuperan calidad (el origen es Opus). — S

## 2. Metadatos y archivos

- [x] **Etiquetas ID3/MP4/FLAC/OGG**: título, artista (creador), álbum (playlist),
  fecha, nº de pista, género (`display_tags`), comentario. — S
- [x] **Portada embebida** en el audio (MP3/M4A/FLAC/OGG). — S
- [x] **Letra embebida** (USLT en ID3, `©lyr` en M4A) + `.txt` y `.lrc` al lado. — S
- [x] **Sidecar `.json`** por pista: todos los campos (modelo, tags, prompt, URL,
  fecha, portada, video). — S
- [x] **Portada de playlist** (`cover.jpg`) en la carpeta. — S
- [x] **Plantilla de nombre de archivo** configurable:
  `{n} {title} {artist} {album} {date} {model}`. — S
- [x] Numeración con padding y saneado de nombres.
- [x] **Manifiesto `.mi_suno.json`** de la carpeta para detectar ya descargados. — M
- [x] Exportar `_playlist.json` y `_playlist.m3u8`. — S
- [ ] Exportar `.csv`/`.nfo` de la playlist. — S

## 3. Contenido extra

- [x] **Canción individual** desde `suno.com/song/{id}` (endpoint confirmado). — S
- [ ] **Descargar solo portadas** de una playlist. — S
- [ ] **Descargar solo letras** (TXT/LRC) de una playlist. — S
- [ ] **Copiar estilo/prompt** al portapapeles. — S
- [x] **Video** cuando `video_url` no está vacío. — M
- [ ] **Perfil de creador**: descargar todas sus playlists públicas
  (investigar `/api/profiles/{handle}`). — L
- [ ] **Álbumes** (campo `albums` de la pista). — M
- [ ] ~~Stems~~ — no disponible públicamente. — —

## 4. Cola y biblioteca

- [x] **Vista previa de la playlist** antes de descargar: lista con título,
  duración, modelo y portada. — M
- [x] **Selección por casilla**: descargar solo las pistas elegidas. — M
- [x] **Búsqueda/filtro** dentro de la playlist. — S
- [x] **Cola multi-playlist** con progreso total. — M
- [x] **Pausar/reanudar** en mitad de la descarga. — M
- [x] **Reintentar fallidos** (solo los que fallaron). — S
- [x] **Historial** de descargas y playlists recientes (menú del reloj). — M
- [ ] **Deduplicación** por `clip.id` entre playlists distintas. — S
- [ ] Reanudar `.part` interrumpidos (hoy se re-descarga). — M
- [ ] Ordenar por título / fecha / duración. — S
- [ ] Exportar/importar la cola. — M

## 5. Red y robustez

- [x] Reintentos con backoff (5/15/30 s).
- [x] Parada inmediata ante 403/429 (con aviso distinto al de "Detener").
- [ ] **Cooldown automático** y reanudación tras el bloqueo. — M
- [x] **Concurrencia configurable** (1–3) manteniendo el trato educado. — M
- [x] Proxy **HTTP y SOCKS5** (PySocks) con validación en ajustes. — S
- [ ] **Lista de proxies** con rotación. — M
- [x] Timeouts y nº de reintentos configurables. — S
- [x] Pausas "humanas" con jitter.
- [ ] **Caché de rights/keys** por pista. — S
- [x] Mensajes claros para playlist privada/inexistente.
- [ ] Descarga resumible con `Range`. — M
- [x] **Log a archivo** (`%APPDATA%\MiSuno\mi_suno.log`). — S

## 6. Interfaz y experiencia

- [x] **Portada de la playlist** en la tarjeta al analizar. — S
- [ ] **Reproductor integrado** (QMediaPlayer) para escuchar antes/después. — L
- [x] **Arrastrar y soltar** enlaces de texto. — S
- [x] **Auto-detección** de enlace Suno en el portapapeles al enfocar. — S
- [x] **Notificación** de escritorio al terminar. — S
- [x] **Bandeja del sistema**: mostrar, abrir carpeta, salir. — M
- [x] Botón **Abrir carpeta** al terminar. — S
- [~] Toasts propios; faltan estados vacíos ilustrados. — S
- [ ] **Tema claro/oscuro** y selector de acento. — M
- [x] **Atajos**: Ctrl+Enter, Ctrl+O, Ctrl+, , Ctrl+F. — S
- [~] Progreso por pista con **velocidad**; falta ETA. — S
- [ ] **Modo mini** / compacto. — M
- [ ] Paleta de comandos Ctrl+K (opcional). — L
- [ ] **Accesibilidad**: foco visible, contraste AA, navegación con teclado,
  escalado de UI. — M
- [~] Vistas adaptables (el bento se estira, sin reflow por debajo de 1060 px). — S

## 7. Ajustes y sistema

- [x] **Persistencia** de ajustes con QSettings. — S
- [ ] **Idioma ES/EN** (i18n). — M
- [x] Carpeta, formato, calidad y plantilla recordadas. — S
- [ ] **Modo portable** (ajustes junto al .exe). — S
- [x] Minimizar a bandeja al cerrar (desactivable). — M
- [ ] Iniciar con Windows. — S
- [x] Comprobar ffmpeg al arrancar y avisar si falta. — M
- [x] `error.log` para fallos sin consola.
- [~] Actualización: botón buscar/descargar con canal JSON (descarga y lanza el
  instalador); falta publicar el canal. — L

## 8. Distribución

- [x] Icono `.ico` multi-tamaño + integración en la app.
- [x] Script de compilación con PyInstaller.
- [x] **Instalador `.msi`** (WiX 3.14): instala en `C:\Program Files\Suno v1`,
  acceso en el menú Inicio, entrada en Aplicaciones instaladas y desinstalador.
  Se compila con `instalador\compilar_instalador.bat`. — M
- [ ] Build **portable ZIP**. — S
- [ ] Firma de código (evitar SmartScreen). — L
- [ ] CI que compile y publique releases. — L

## 9. Límites y honestidad

- Solo playlists **públicas**; nunca cuentas ni bibliotecas privadas.
- No se eluden las cuotas de descarga de Suno: se usa el mismo audio público
  que sirve el reproductor web.
- WAV/FLAC **no** mejoran la calidad: el origen es Opus con pérdida.
- Stems y video solo cuando Suno los expone públicamente.
- Respetar los derechos de los autores y los Términos de Suno.

---

## Lo que falta, en orden de valor

1. **Reproductor integrado** (QMediaPlayer) — escuchar sin salir de la app.
2. **Reanudar `.part`** y descarga por `Range` — redes inestables.
3. **Cooldown automático** tras 403/429 — descargas largas sin microgestión.
4. **Tema claro / i18n** — comodidad, no potencia.
5. **Portable ZIP** — repartir sin instalación (el instalador ya está hecho).
