package com.dancenot.sunov1

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
import android.util.Base64

/**
 * Cliente de la API pública de Suno + descifrado del audio ("esquema Mango").
 * Es el mismo procedimiento que usa el reproductor web: pedir los derechos,
 * desenvolver la clave con AES-GCM y descifrar el archivo con AES-CTR.
 */
object SunoApi {

    private const val API_PLAYLIST = "https://studio-api.prod.suno.com/api/playlist/%s?page=%d"
    private const val API_RIGHTS = "https://studio-api.prod.suno.com/api/mango/rights"
    private const val UA =
        "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) " +
            "Chrome/128.0.0.0 Mobile Safari/537.36"

    data class Track(
        val id: String,
        val title: String,
        val duration: Int,
        val model: String,
        val genre: String,
        val created: String,
        val cover: String,
        val lyrics: String,
        val mediaUrl: String,
    )

    data class Playlist(
        val id: String,
        val name: String,
        val author: String,
        val cover: String,
        val tracks: List<Track>,
    )

    class Bloqueado(causa: String) : IOException(causa)

    // ------------------------------------------------------------- peticiones
    private fun abrir(url: String, metodo: String = "GET", referer: String? = null): HttpURLConnection {
        val conexion = URL(url).openConnection() as HttpURLConnection
        conexion.requestMethod = metodo
        conexion.connectTimeout = 15000
        conexion.readTimeout = 60000
        conexion.setRequestProperty("User-Agent", UA)
        conexion.setRequestProperty("Accept", "application/json, text/plain, */*")
        conexion.setRequestProperty("Accept-Language", "en-US,en;q=0.9")
        conexion.setRequestProperty("Origin", "https://suno.com")
        if (referer != null) conexion.setRequestProperty("Referer", referer)
        return conexion
    }

    private fun leerJson(url: String, referer: String): JSONObject {
        val c = abrir(url, "GET", referer)
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

    fun idDePlaylist(texto: String): String {
        val m = Regex("suno\\.com/playlist/([0-9a-fA-F-]{30,40})").find(texto.trim())
        if (m != null) return m.groupValues[1].trim('/', '?', ' ')
        val solo = Regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
        if (solo.matches(texto.trim())) return texto.trim().lowercase()
        throw IllegalArgumentException("Ese enlace no es de una playlist de Suno")
    }

    fun playlist(id: String): Playlist {
        val referer = "https://suno.com/playlist/$id"
        val vistas = LinkedHashMap<String, Pair<Double, JSONObject>>()
        var meta: JSONObject? = null
        var pagina = 1
        while (pagina <= 20) {
            val datos = leerJson(API_PLAYLIST.format(id, pagina), referer)
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
            .mapNotNull { (_, par) -> convertir(par.second) }

        return Playlist(
            id = id,
            name = base.optString("name").ifBlank { "Sin título" },
            author = base.optString("user_display_name").ifBlank { base.optString("display_name") },
            cover = base.optString("image_url"),
            tracks = pistas,
        )
    }

    private fun convertir(clip: JSONObject): Track? {
        val cid = clip.optString("id").ifBlank { return null }
        val meta = clip.optJSONObject("metadata") ?: JSONObject()
        val media = mejorMedia(clip.optJSONArray("media_urls"))
        return Track(
            id = cid,
            title = clip.optString("title").ifBlank { "Sin título" },
            duration = meta.optInt("duration", 0),
            model = clip.optString("model_name").ifBlank { clip.optString("major_model_version") },
            genre = meta.optString("tags"),
            created = clip.optString("created_at").take(10),
            cover = clip.optString("image_large_url").ifBlank { clip.optString("image_url") },
            lyrics = meta.optString("prompt"),
            mediaUrl = media,
        )
    }

    private fun mejorMedia(lista: org.json.JSONArray?): String {
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
    private fun derechos(clipId: String): JSONObject {
        var ultimo: Exception? = null
        repeat(3) { intento ->
            try {
                val c = abrir(API_RIGHTS, "POST", "https://suno.com/")
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

    // ------------------------------------------------------------- descarga
    fun descargarAudio(track: Track, destino: File, aviso: (String) -> Unit = {}) {
        if (track.mediaUrl.isEmpty()) throw IOException("la pista no tiene audio público")
        aviso("Conectando con Suno…")
        val conexion = abrir(track.mediaUrl, "GET", "https://suno.com/")
        conexion.instanceFollowRedirects = true
        val buffer = ByteArray(64 * 1024)
        val salida = java.io.ByteArrayOutputStream()
        try {
            val codigo = conexion.responseCode
            android.util.Log.d("SunoX", "http=$codigo len=${conexion.contentLength}")
            if (codigo == 403 || codigo == 429) {
                throw Bloqueado("Suno pidió calma ($codigo)")
            }
            if (codigo !in 200..299) throw IOException("HTTP $codigo")
            val total = conexion.contentLength
            conexion.inputStream.use { entrada ->
                var leido = 0
                var ultimo = -1
                while (true) {
                    val n = entrada.read(buffer)
                    if (n <= 0) break
                    salida.write(buffer, 0, n)
                    leido += n
                    if (total > 0) {
                        val pct = leido * 100 / total
                        if (pct / 10 != ultimo) {
                            ultimo = pct / 10
                            aviso("Descargando audio $pct%")
                        }
                    }
                }
            }
        } finally {
            conexion.disconnect()
        }
        val crudo = salida.toByteArray()
        android.util.Log.d("SunoX", "audio ${crudo.size} bytes")
        aviso("Pidiendo la clave…")
        val derechos = derechos(track.id)
        aviso("Descifrando…")
        val claro = descifrar(crudo, track.id, derechos)
        android.util.Log.d("SunoX", "claro ${claro.size} bytes")
        destino.parentFile?.mkdirs()
        destino.writeBytes(claro)
        aviso("Audio listo.")
    }

    fun descargarImagen(url: String): ByteArray? {
        if (url.isEmpty()) return null
        return try {
            val c = abrir(url, "GET", "https://suno.com/")
            val datos = c.inputStream.use { it.readBytes() }
            c.disconnect()
            datos
        } catch (e: Exception) {
            null
        }
    }
}
