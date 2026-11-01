# Marketing — video de Suno v1

Pieza **"De la nube a tu carpeta"**: 73,7 s, 1920×1080, 30 fps, español (es-MX-JorgeNeural +4 %).

- Guion y dirección: [`guion.md`](guion.md)
- Video final: [`video/promo-full-con-audio.mp4`](video/promo-full-con-audio.mp4)
- Portada para publicarlo: [`video/portada.png`](video/portada.png)

## Cómo está hecho

Todo se genera en local, sin grabar pantalla y sin servicios en la nube:

| Pieza | Archivo | Qué hace |
| --- | --- | --- |
| Voz | `voz.py` | edge-tts por bloques + fronteras de palabra → `audio/timeline.json` |
| Subtítulos y SFX | `exportar.py` | `audio/subs.json`, `audio/sfx.json` |
| Música y efectos | `musica.py` | sintetizados con numpy (batería, bajo, pad, arpegio, 14 efectos) y mezclados con la voz (ducking) → `audio/mezcla.wav` |
| Imagen | `promo.html` | escenas en HTML/CSS/JS con `window.pintar(t)` determinista |
| Render | `render.py` | Chrome headless por CDP: pinta cada frame y lo manda a ffmpeg (H.264 CRF 15) |
| Todo junto | `construir.py` | voz → subtítulos → música → render |

```bash
python marketing/construir.py            # video completo
python marketing/construir.py --rapido   # versión de revisión (CRF 22)
python marketing/render.py --foto 25,41  # fotogramas sueltos para revisar
```

El servidor local sirve la raíz del repo (`http://127.0.0.1:PUERTO/marketing/promo.html`) porque las capturas están en `assets/` y `marketing/capturas/`.

## Cambiar el guion

1. Edita los textos en `voz.py` (`BLOQUES`); cada bloque es una escena.
2. Vuelve a lanzar `construir.py`. La duración de cada escena se ajusta sola a la voz: no hay tiempos a mano.
3. Si cambias la coreografía, ajusta los efectos en `comun.py` (`SFX`) y los tiempos de la escena en `promo.html` (los `seg(u, a, b)`).

## Requisitos

`pip install edge-tts pillow numpy websocket-client` · Chrome instalado · `herramientas/ffmpeg.exe`.

Las capturas son reales: `assets/app-v1.png` (escritorio) y `marketing/capturas/android-3.png` (móvil, tomada del ZTE con `adb`).
