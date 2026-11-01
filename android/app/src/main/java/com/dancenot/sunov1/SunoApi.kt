package com.dancenot.sunov1

import android.util.Base64
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest
import javax.crypto.Cipher
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.IvParameterSpec
import javax.crypto.spec.SecretKeySpec

/**
 * Cliente de la API publica de Suno + descifrado del audio ("esquema Mango").
 * Es el mismo procedimiento que usa el reproductor web: pedir los derechos,
 * desenvolver la clave con AES-GCM y descifrar el archivo con AES-CTR.
 */
object SunoApi {

    private const val API_PLAYLIST = "https://studio-api.prod.suno.com/api/playlist/%s?page=%d"
    private const val API_CLIP = "https://studio-api.prod.suno.com/api/clip/%s"
    private const val API_RIGHTS = "https://studio-api.prod.suno.com/api/mango/rights"
    private const val UA =
        "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) " +
            "Chrome/128.0.0.0 Mobile Safari/537.36"

    enum class Tipo { PLAYLIST, SONG }

    data class Enlace(val tipo: Tipo, val id: String)

    data class Track(
        val id: String,
        val titulo: String,
        val duracion: Int,
        val modelo: String,
        val genero: String,
        val fecha: String,
        val portada: String,
        val video: String,
        val letra: String,
        val audioUrl: String,
    )

    data class Playlist(
        val id: String,
        val nombre: String,
        val autor: String,
        val portada: String,
        val descripcion: String,
        val total: Double,
        val tipo: Tipo,
        val pistas: List<Track>,
    )

    class Bloqueado(causa: String) : IOException(causa)

    // ------------------------------------------------------------- peticiones
    private fun abrir(
        url: String,
        metodo: String = "GET",
        referer: String? = null,
        timeoutS: Int = 60,
    ): HttpURLConnection {
        val conexion = URL(url).openConnection() as HttpURLConnection
        conexion.requestMethod = metodo
        conexion.connectTimeout = 15000
        conexion.readTimeout = timeoutS * 1000
        conexion.setRequestProperty("User-Agent", UA)
        conexion.setRequestProperty("Accept", "application/json, text/plain, */*")
        conexion.setRequestProperty("Accept-Language", "en-US,en;q=0.9")
        conexion.setRequestProperty("Origin", "https://suno.com")
        if (referer != null) conexion.setRequestProperty("Referer", referer)
        return conexion
    }

    private fun leerJson(url: String, referer: String, timeoutS: Int): JSONObject {
        val c = abrir(url, "GET", referer, timeoutS)
        try {
            if (c.responseCode == 403 || c.responseCode == 429) {
                throw Bloqueado("Suno pidió calma (${c.responseCode})")
            }
            if (c.responseCode !in 200..299) throw IOException("HTTP ${c.responseCode}")
            return JSONObject(c.inputStream.bufferedReader().readText())
        } finally {
            c.disconnect()
        }
    }

    /** Acepta enlaces de playlist, de canción, o un id suelto. Una por línea. */
    fun leerEnlaces(texto: String): List<Enlace> {
        val salida = LinkedHashMap<String, Enlace>()
        for (linea in texto.lines()) {
            val t = linea.trim()
            if (t.isEmpty()) continue
            val m = Regex("suno\\.com/(playlist|song)/([0-9a-fA-F-]{30,40})").find(t)
            if (m != null) {
                val id = m.groupValues[2].trim('/', '?', ' ')
                val tipo = if (m.groupValues[1] == "playlist") Tipo.PLAYLIST else Tipo.SONG
                salida["$tipo-$id"] = Enlace(tipo, id)
                continue
            }
            if (Regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
                    .matches(t)
            ) {
                salida["PLAYLIST-${t.lowercase()}"] = Enlace(Tipo.PLAYLIST, t.lowercase())
            }
        }
        if (salida.isEmpty()) throw IllegalArgumentException("No hay enlaces de Suno válidos")
        return salida.values.toList()
    }

    fun idDePlaylist(texto: String): String {
        val primero = leerEnlaces(texto).firstOrNull()
            ?: throw IllegalArgumentException("Ese enlace no es de Suno")
        return primero.id
    }

    // --------------------------------------------------------------- lectura
    fun cargar(enlace: Enlace, timeoutS: Int = 60): Playlist =
        if (enlace.tipo == Tipo.SONG) cancion(enlace.id, timeoutS)
        else playlist(enlace.id, timeoutS)

    private fun cancion(id: String, timeoutS: Int): Playlist {
        val clip = leerJson(API_CLIP.format(id), "https://suno.com", timeoutS)
        val pista = convertir(clip) ?: throw IOException("Esa canción no tiene datos")
        return Playlist(
            id = id,
            nombre = pista.titulo,
            autor = clip.optString("display_name"),
            portada = pista.portada,
            descripcion = "",
            total = pista.duracion.toDouble(),
            tipo = Tipo.SONG,
            pistas = listOf(pista),
        )
    }

    private fun playlist(id: String, timeoutS: Int): Playlist {
        val referer = "https://suno.com/playlist/$id"
        val vistas = LinkedHashMap<String, Pair<Double, JSONObject>>()
        var meta: JSONObject? = null
        var pagina = 1
        while (pagina <= 20) {
            val datos = leerJson(API_PLAYLIST.format(id, pagina), referer, timeoutS)
            meta = datos
            val lote = datos.optJSONArray("playlist_clips") ?: break
            var nuevas = 0
            for (i in 0 until lote.length()) {
                val item = lote.optJSONObject(i) ?: continue
                val clip = item.optJSONObject("clip") ?: continue
                val cid = clip.optString("id")
                if (cid.isEmpty() || vistas.containsKey(cid)) continue
                val pos = item.optDouble("relative_index", (vistas.size + 1).toDouble())
                vistas[cid] = pos to clip
                nuevas++
            }
            val total = datos.optInt("num_total_results", vistas.size)
            if (nuevas == 0 || vistas.size >= total) break
            pagina++
        }
        val base = meta ?: throw IOException("Respuesta vacía de Suno")
        val pistas = vistas.entries
            .sortedBy { it.value.first }
            .mapNotNull { convertir(it.value.second) }

        return Playlist(
            id = id,
            nombre = base.optString("name").ifBlank { "Sin título" },
            autor = base.optString("user_display_name").ifBlank { base.optString("display_name") },
            portada = base.optString("image_url"),
            descripcion = base.optString("description"),
            total = base.optDouble("total_duration", 0.0),
            tipo = Tipo.PLAYLIST,
            pistas = pistas,
        )
    }

    private fun convertir(clip: JSONObject): Track? {
        val cid = clip.optString("id").ifBlank { return null }
        val meta = clip.optJSONObject("metadata") ?: JSONObject()
        val media = mejorMedia(clip.optJSONArray("media_urls"))
        return Track(
            id = cid,
            titulo = clip.optString("title").ifBlank { "Sin título" },
            duracion = meta.optInt("duration", clip.optInt("duration", 0)),
            modelo = clip.optString("major_model_version")
                .ifBlank { clip.optString("model_name") },
            genero = clip.optString("display_tags").ifBlank { meta.optString("tags") },
            fecha = clip.optString("created_at").take(10),
            portada = clip.optString("image_large_url").ifBlank { clip.optString("image_url") },
            video = clip.optString("video_url"),
            letra = meta.optString("prompt"),
            audioUrl = media,
        )
    }

    private fun mejorMedia(lista: JSONArray?): String {
        if (lista == null) return ""
        for (i in 0 until lista.length()) {
            val m = lista.optJSONObject(i) ?: continue
            val url = m.optString("url")
            if (url.isEmpty()) continue
            val tipo = m.optString("content_type").lowercase()
            val entrega = m.optString("delivery").lowercase()
            if (entrega.isNotEmpty() && entrega != "progressive") continue
            if (tipo.startsWith("video") || tipo == "mp4") continue
            return url
        }
        return ""
    }

    // --------------------------------------------------------------- derechos
    private fun derechos(clipId: String, timeoutS: Int): JSONObject {
        var ultimo: Exception? = null
        repeat(3) { intento ->
            try {
                val c = abrir(API_RIGHTS, "POST", "https://suno.com/", timeoutS)
                c.doOutput = true
                c.setRequestProperty("Content-Type", "application/json")
                val cuerpo = """{"content_params":{"content_id":"$clipId","content_type":"clip"}}"""
                c.outputStream.use { it.write(cuerpo.toByteArray()) }
                if (c.responseCode == 403 || c.responseCode == 429) {
                    throw Bloqueado("Suno pidió calma (${c.responseCode})")
                }
                if (c.responseCode !in 200..299) throw IOException("HTTP ${c.responseCode}")
                val datos = JSONObject(c.inputStream.bufferedReader().readText())
                c.disconnect()
                if (datos.optString("key").isEmpty() || datos.optString("iv").isEmpty() ||
                    datos.optString("glt").isEmpty()
                ) {
                    throw IOException("respuesta de derechos incompleta")
                }
                return datos
            } catch (e: Bloqueado) {
                throw e
            } catch (e: Exception) {
                ultimo = e
                if (intento < 2) Thread.sleep((intento + 1) * 3000L)
            }
        }
        throw IOException("no se pudo pedir la clave: ${ultimo?.message}")
    }

    private fun sha256(texto: String): ByteArray =
        MessageDigest.getInstance("SHA-256").digest(texto.toByteArray())

    private fun desenvolver(wrapped: String, clipId: String, clave: ByteArray): ByteArray {
        val w = Base64.decode(wrapped, Base64.DEFAULT)
        val nonce = w.copyOfRange(0, 12)
        val cifrado = w.copyOfRange(12, w.size - 16)
        val etiqueta = w.copyOfRange(w.size - 16, w.size)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, SecretKeySpec(clave, "AES"), GCMParameterSpec(128, nonce))
        cipher.updateAAD(clipId.toByteArray())
        return cipher.doFinal(cifrado + etiqueta)
    }

    fun descifrar(datos: ByteArray, clipId: String, derechos: JSONObject): ByteArray {
        val claveUsuario = sha256(derechos.getString("glt"))
        val clave = desenvolver(derechos.getString("key"), clipId, claveUsuario)
        val contador = desenvolver(derechos.getString("iv"), clipId, claveUsuario)
        val cipher = Cipher.getInstance("AES/CTR/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, SecretKeySpec(clave, "AES"), IvParameterSpec(contador))
        return cipher.doFinal(datos)
    }

    // ------------------------------------------------------------- descargas
    /**
     * Baja una URL al archivo indicado, con reintentos y progreso.
     * Devuelve los bytes escritos. Lanza [Bloqueado] si Suno nos frena.
     */
    fun descargar(
        url: String,
        destino: File,
        referer: String,
        timeoutS: Int,
        reintentos: Int,
        alProgreso: (Long, Long, Double) -> Unit = { _, _, _ -> },
    ): Long {
        if (url.isEmpty()) throw IOException("sin archivo disponible")
        var ultimo: Exception? = null
        for (intento in 0 until reintentos.coerceAtLeast(1)) {
            try {
                val conexion = abrir(url, "GET", referer, timeoutS)
                conexion.instanceFollowRedirects = true
                try {
                    val codigo = conexion.responseCode
                    if (codigo == 403 || codigo == 429) {
                        throw Bloqueado("Suno pidió calma ($codigo)")
                    }
                    if (codigo !in 200..299) throw IOException("HTTP $codigo")
                    val total = conexion.contentLength.toLong()
                    destino.parentFile?.mkdirs()
                    var escrito = 0L
                    val inicio = System.currentTimeMillis()
                    conexion.inputStream.use { entrada ->
                        destino.outputStream().use { salida ->
                            val buffer = ByteArray(64 * 1024)
                            while (true) {
                                val n = entrada.read(buffer)
                                if (n <= 0) break
                                salida.write(buffer, 0, n)
                                escrito += n
                                val seg = ((System.currentTimeMillis() - inicio) / 1000.0)
                                    .coerceAtLeast(0.05)
                                alProgreso(escrito, total, escrito / seg)
                            }
                        }
                    }
                    if (escrito == 0L) throw IOException("archivo vacío")
                    return escrito
                } finally {
                    conexion.disconnect()
                }
            } catch (e: Bloqueado) {
                throw e
            } catch (e: Exception) {
                ultimo = e
                if (intento < reintentos - 1) Thread.sleep(4000L * (intento + 1))
            }
        }
        throw IOException("descarga fallida: ${ultimo?.message}")
    }

    /** Descarga el audio original de una pista y lo deja descifrado en [destino]. */
    fun descargarAudio(
        track: Track,
        destino: File,
        referer: String,
        timeoutS: Int,
        reintentos: Int,
        alProgreso: (Long, Long, Double) -> Unit = { _, _, _ -> },
    ) {
        descargar(track.audioUrl, destino, referer, timeoutS, reintentos, alProgreso)
        val derechos = derechos(track.id, timeoutS)
        val claro = descifrar(destino.readBytes(), track.id, derechos)
        destino.writeBytes(claro)
    }

    fun descargarImagen(url: String, timeoutS: Int = 30): ByteArray? {
        if (url.isEmpty()) return null
        return try {
            val c = abrir(url, "GET", "https://suno.com/", timeoutS)
            val datos = c.inputStream.use { it.readBytes() }
            c.disconnect()
            datos
        } catch (_: Exception) {
            null
        }
    }
}
