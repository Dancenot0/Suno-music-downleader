package com.dancenot.sunov1

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import java.text.Normalizer
import java.util.Collections

/**
 * Motor de descargas: réplica del `engine.Engine` del escritorio
 * (pausa, reintentos, omisión de lo ya descargado, vídeo, archivos aparte).
 */
class Motor(
    private val contexto: Context,
    private val opciones: Ajustes,
) {
    data class Resultado(
        val ok: Int,
        val saltadas: Int,
        val fallidas: List<String>,
        val fallidasIds: List<String>,
        val cancelado: Boolean,
        val bloqueado: Boolean,
    )

    private data class Plan(
        val playlist: SunoApi.Playlist,
        val track: SunoApi.Track,
        val numero: Int,
        val carpeta: String,
        val referer: String,
        val portada: ByteArray?,
    )

    val registro: MutableList<String> = Collections.synchronizedList(mutableListOf<String>())

    @Volatile var avance: Float = 0f
    @Volatile var estado: String = "Preparando…"
    @Volatile var pista: String = ""
    @Volatile var hechas: Int = 0
    @Volatile var total: Int = 0
    @Volatile var pausado: Boolean = false
        private set
    @Volatile var ultimoAviso: String = ""

    @Volatile private var cancelado = false
    @Volatile private var bloqueado = false
    @Volatile private var enPausa = false
    @Volatile private var terminado = false

    fun pausar(valor: Boolean) {
        enPausa = valor
        pausado = valor
        avisar(if (valor) "En pausa." else "Reanudando…")
    }

    fun detener() {
        cancelado = true
        enPausa = false
        pausado = false
        avisar("Deteniendo…")
    }

    fun cancelado() = cancelado
    fun finalizado() = terminado

    // ------------------------------------------------------------------ util
    private fun avisar(texto: String) {
        estado = texto
        registro.add(texto)
        while (registro.size > 120) registro.removeAt(0)
    }

    private fun esperar() {
        while (enPausa && !cancelado) Thread.sleep(150)
    }

    private fun limpiar(texto: String): String {
        val normal = Normalizer.normalize(texto, Normalizer.Form.NFC)
        val sin = normal.replace(Regex("[\\\\/:*?\"<>|\\r\\n\\t]+"), " ")
            .replace(Regex("\\s+"), " ")
            .trim(' ', '.')
        return sin.take(110).ifBlank { "Sin título" }
    }

    private fun velocidad(bps: Double): String = when {
        bps >= 1024 * 1024 -> String.format("%.1f MB/s", bps / (1024 * 1024))
        bps >= 1024 -> String.format("%.0f KB/s", bps / 1024)
        else -> String.format("%.0f B/s", bps)
    }

    private fun tamano(bytes: Long): String = when {
        bytes >= 1024 * 1024 -> String.format("%.1f MB", bytes / (1024.0 * 1024))
        bytes >= 1024 -> String.format("%.0f KB", bytes / 1024.0)
        else -> "$bytes B"
    }

    private fun nombre(plan: Plan): String {
        val t = plan.track
        val ancho = plan.playlist.pistas.size.toString().length.coerceAtLeast(1)
        val campos = mapOf(
            "n" to plan.numero.toString().padStart(ancho, '0'),
            "title" to t.titulo,
            "artist" to plan.playlist.autor.ifBlank { "Suno" },
            "album" to plan.playlist.nombre,
            "date" to t.fecha,
            "model" to t.modelo,
        )
        var nombre = opciones.plantilla.ifBlank { "{n} - {title}" }
        for ((k, v) in campos) nombre = nombre.replace("{$k}", v)
        return limpiar(nombre)
    }

    // --------------------------------------------------------------- ejecutar
    suspend fun ejecutar(
        playlists: List<SunoApi.Playlist>,
        seleccion: Set<String>,
    ): Resultado = withContext(Dispatchers.IO) {
        val planes = ArrayList<Plan>()
        for (pl in playlists) {
            if (cancelado) break
            val elegidas = pl.pistas.filter { it.id in seleccion }
            if (elegidas.isEmpty()) continue
            avisar("[${pl.nombre}] ${elegidas.size} pista(s)")
            val carpeta = if (opciones.subcarpeta) {
                "${opciones.destino}/${limpiar(pl.nombre)}"
            } else {
                opciones.destino
            }
            val referer = if (pl.tipo == SunoApi.Tipo.PLAYLIST) {
                "https://suno.com/playlist/${pl.id}"
            } else {
                "https://suno.com"
            }
            val portada = if ((opciones.portada || opciones.aparte) && pl.portada.isNotEmpty()) {
                SunoApi.descargarImagen(pl.portada, opciones.timeoutS)
            } else {
                null
            }
            pl.pistas.forEachIndexed { i, t ->
                if (t.id in seleccion) planes += Plan(pl, t, i + 1, carpeta, referer, portada)
            }
        }

        total = planes.size
        avance = 0f
        if (planes.isEmpty()) {
            terminado = true
            return@withContext Resultado(0, 0, emptyList(), emptyList(), false, false)
        }

        var ok = 0
        var saltadas = 0
        val fallidas = mutableListOf<String>()
        val fallidasIds = mutableListOf<String>()

        for ((i, plan) in planes.withIndex()) {
            if (cancelado) break
            esperar()
            if (cancelado) break
            try {
                val resultado = una(plan, i)
                when (resultado) {
                    "saltada" -> saltadas++
                    else -> ok++
                }
            } catch (e: SunoApi.Bloqueado) {
                bloqueado = true
                avisar("Suno pidió reducir velocidad (403/429). Deteniendo.")
                cancelado = true
                break
            } catch (e: Exception) {
                fallidas += plan.track.titulo
                fallidasIds += plan.track.id
                avisar("✗ ${plan.track.titulo}: ${e.message?.take(60)}")
            }
            hechas = i + 1
            avance = (i + 1).toFloat() / total
            if (i < planes.size - 1 && !cancelado) {
                pista = ""
                esperar()
                val espera = opciones.pausaMs + (0..opciones.pausaMs).random()
                var restante = espera
                while (restante > 0 && !cancelado) {
                    esperar()
                    val paso = 100
                    delay(paso.toLong())
                    restante -= paso
                }
            }
        }

        terminado = true
        Resultado(ok, saltadas, fallidas, fallidasIds, cancelado, bloqueado)
    }

    /** Devuelve "ok" o "saltada". */
    private fun una(plan: Plan, indice: Int): String {
        val t = plan.track
        esperar()
        if (cancelado) throw IllegalStateException("cancelado")

        val esVideo = opciones.video && t.video.isNotBlank()
        val base = nombre(plan)
        val nombre = base + if (esVideo) ".mp4" else ".m4a"

        if (opciones.omitir) {
            val yaEsta = if (esVideo) {
                Almacen.existeVideo(contexto, nombre, plan.carpeta)
            } else {
                Almacen.existeAudio(contexto, nombre, plan.carpeta)
            }
            if (yaEsta) {
                avisar("= ${t.titulo} (ya está)")
                return "saltada"
            }
        } else if (!esVideo &&
            Almacen.existeAudio(contexto, nombre, plan.carpeta) &&
            !Almacen.borrarAudio(contexto, nombre, plan.carpeta)
        ) {
            // El archivo existe pero no es nuestro (de otra instalación):
            // mejor no duplicarlo con "(1)".
            avisar("= ${t.titulo} (ya está y no se puede reemplazar)")
            return "saltada"
        }

        pista = t.titulo
        estado = "${t.titulo} · bajando…"

        val cache = File(contexto.cacheDir, "suno").apply { mkdirs() }
        val temporal = File(cache, "suno-${t.id}${if (esVideo) ".mp4" else ".m4a"}")

        val progreso: (Long, Long, Double) -> Unit = { escrito, totalBytes, velocidad ->
            if (!enPausa && !cancelado) {
                val fraccion = if (totalBytes > 0) {
                    escrito.toDouble() / totalBytes
                } else {
                    0.0
                }
                avance = ((indice + fraccion) / total).toFloat().coerceIn(0f, 1f)
                estado = "${t.titulo} · ${(fraccion * 100).toInt()}% · " +
                    velocidad(velocidad)
            }
        }

        try {
            if (esVideo) {
                SunoApi.descargar(
                    t.video, temporal, plan.referer,
                    opciones.timeoutS, opciones.reintentos, progreso
                )
                Almacen.guardarVideo(contexto, temporal, nombre, plan.carpeta)
            } else {
                SunoApi.descargarAudio(
                    t, temporal, plan.referer,
                    opciones.timeoutS, opciones.reintentos, progreso
                )
                val fallo = Etiquetas.escribir(
                    temporal, t, plan.playlist.nombre, plan.playlist.autor, plan.numero,
                    plan.portada, opciones.etiquetas, opciones.portada, opciones.letras
                )
                if (fallo != null) avisar("· ${t.titulo}: sin etiquetas ($fallo)")
                Almacen.guardarAudio(contexto, temporal, nombre, plan.carpeta)
                if (opciones.aparte) extras(plan, base)
            }
            avisar("✓ $nombre (${tamano(temporal.length())})")
            return "ok"
        } finally {
            temporal.delete()
        }
    }

    private fun extras(plan: Plan, base: String) {
        val t = plan.track
        try {
            if (t.letra.isNotBlank()) {
                val lrc = buildString {
                    appendLine("[ti:${t.titulo}]")
                    appendLine("[ar:${plan.playlist.autor.ifBlank { "Suno" }}]")
                    appendLine("[al:${plan.playlist.nombre}]")
                    appendLine()
                    append(t.letra)
                }
                Almacen.guardarTexto(
                    contexto, lrc, "$base.lrc", "application/octet-stream"
                )
            }
            val ficha = JSONObject()
                .put("id", t.id)
                .put("title", t.titulo)
                .put("artist", plan.playlist.autor)
                .put("album", plan.playlist.nombre)
                .put("playlist", plan.playlist.id)
                .put("date", t.fecha)
                .put("model", t.modelo)
                .put("tags", t.genero)
                .put("cover", t.portada)
                .put("video", t.video)
                .put("lyrics", t.letra)
            Almacen.guardarTexto(
                contexto, ficha.toString(1), "$base.json", "application/json"
            )
        } catch (e: Exception) {
            ultimoAviso = "archivos aparte: ${e.message?.take(60)}"
            avisar("· ${t.titulo}: sin archivos aparte (${e.message?.take(40)})")
        }
    }
}
