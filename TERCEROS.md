# Créditos y componentes de terceros

Suno v1 no existiría sin trabajo ajeno. Esta página deja claro qué es de quién.

---

## 1. Núcleo de descarga — MIT © zarigata

El archivo `suno_dl.py` y parte de la lógica de consulta a la API pública de Suno
provienen del proyecto **sudodownloader**:

- Repositorio: <https://github.com/zarigata/sudodownloader>
- Autor: **zarigata**
- Licencia: **MIT**

Texto de la licencia (también en el archivo [`LICENSE`](LICENSE) de este repositorio):

```
MIT License

Copyright (c) 2026 zarigata

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

**Qué significa:** cualquiera puede usar, copiar, modificar y redistribuir *ese
archivo y lo que derive de él*, siempre que conserve el aviso de copyright y el
texto de la licencia. Esa libertad no se puede quitar y convive con la licencia
del resto de Suno v1 ([`LICENCIA.md`](LICENCIA.md)), que solo cubre el trabajo
propio: interfaz, motor, instalador y web.

---

## 2. ffmpeg

- Proyecto: <https://ffmpeg.org>
- Licencia: **LGPL 2.1 o superior** (las compilaciones con GPL usan **GPL**; la
  incluida en Suno v1 se distribuye con sus avisos correspondientes).
- Uso en Suno v1: conversión de formatos, normalización y etiquetado de audio.
- El binario se incluye sin modificaciones, en `herramientas\ffmpeg.exe`.

## 3. Qt y PySide6

- Qt: <https://www.qt.io> · **LGPL v3**
- PySide6 (enlaces oficiales de Qt para Python): **LGPL v3**
- Uso en Suno v1: toda la interfaz gráfica.
- No se ha modificado ninguna biblioteca de Qt.

## 4. Otras bibliotecas de Python

| Biblioteca | Licencia | Uso |
|---|---|---|
| `requests` | Apache 2.0 | peticiones HTTP |
| `mutagen` | GPL 2.0 | etiquetas, carátulas y letras |
| `PySocks` | BSD | proxy SOCKS5 |
| `urllib3`, `certifi`, `charset-normalizer`, `idna` | MIT / Apache / BSD | transporte HTTP |

---

## 5. Marcas

«Suno» es una marca de sus titulares. Suno v1 es un proyecto independiente: **no
está afiliado, patrocinado ni respaldado por Suno**. El nombre se usa únicamente
para describir con qué servicio funciona.
