package com.dancenot.sunov1

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

/** Preferencias de la app (equivalente a la configuracion del escritorio). */
data class Ajustes(
    val pausaMs: Int = 1500,
    val reintentos: Int = 2,
    val timeoutS: Int = 60,
    val notificar: Boolean = true,
    val destino: String = MUSICA,
    val plantilla: String = "{n} - {title}",
    val etiquetas: Boolean = true,
    val portada: Boolean = true,
    val letras: Boolean = true,
    val aparte: Boolean = false,
    val video: Boolean = false,
    val omitir: Boolean = true,
    val subcarpeta: Boolean = false,
) {
    companion object {
        const val MUSICA = "Music/Suno v1"
        const val DESCARGAS = "Download/Suno v1"
        private const val FICHERO = "suno_v1"

        private fun p(c: Context) =
            c.applicationContext.getSharedPreferences(FICHERO, Context.MODE_PRIVATE)

        fun cargar(c: Context): Ajustes {
            val p = p(c)
            return Ajustes(
                pausaMs = p.getInt("pausa", 1500),
                reintentos = p.getInt("reintentos", 2),
                timeoutS = p.getInt("timeout", 60),
                notificar = p.getBoolean("notificar", true),
                destino = p.getString("destino", MUSICA) ?: MUSICA,
                plantilla = p.getString("plantilla", "{n} - {title}") ?: "{n} - {title}",
                etiquetas = p.getBoolean("etiquetas", true),
                portada = p.getBoolean("portada", true),
                letras = p.getBoolean("letras", true),
                aparte = p.getBoolean("aparte", false),
                video = p.getBoolean("video", false),
                omitir = p.getBoolean("omitir", true),
                subcarpeta = p.getBoolean("subcarpeta", false),
            )
        }

        fun guardar(c: Context, a: Ajustes) {
            p(c).edit()
                .putInt("pausa", a.pausaMs)
                .putInt("reintentos", a.reintentos)
                .putInt("timeout", a.timeoutS)
                .putBoolean("notificar", a.notificar)
                .putString("destino", a.destino)
                .putString("plantilla", a.plantilla)
                .putBoolean("etiquetas", a.etiquetas)
                .putBoolean("portada", a.portada)
                .putBoolean("letras", a.letras)
                .putBoolean("aparte", a.aparte)
                .putBoolean("video", a.video)
                .putBoolean("omitir", a.omitir)
                .putBoolean("subcarpeta", a.subcarpeta)
                .apply()
        }
    }
}

/** Playlists analizadas anteriormente. */
data class Reciente(
    val id: String,
    val nombre: String,
    val autor: String,
    val pistas: Int,
    val tipo: String,
)

object Historial {
    private const val CLAVE = "historial"
    private const val MAXIMO = 24

    private fun prefs(c: Context) = c.applicationContext
        .getSharedPreferences("suno_v1", Context.MODE_PRIVATE)

    fun leer(c: Context): List<Reciente> {
        val crudo = prefs(c).getString(CLAVE, "") ?: return emptyList()
        return try {
            val lista = JSONArray(crudo)
            (0 until lista.length()).mapNotNull { i ->
                val o = lista.optJSONObject(i) ?: return@mapNotNull null
                val id = o.optString("id")
                if (id.isEmpty()) return@mapNotNull null
                Reciente(
                    id = id,
                    nombre = o.optString("nombre"),
                    autor = o.optString("autor"),
                    pistas = o.optInt("pistas"),
                    tipo = o.optString("tipo", "playlist"),
                )
            }
        } catch (_: Exception) {
            emptyList()
        }
    }

    fun apuntar(c: Context, pl: SunoApi.Playlist) {
        val previos = leer(c).filter { it.id != pl.id }
        val nuevos = listOf(
            Reciente(pl.id, pl.nombre, pl.autor, pl.pistas.size, pl.tipo.name.lowercase())
        ) + previos
        val lista = JSONArray()
        nuevos.take(MAXIMO).forEach {
            lista.put(
                JSONObject()
                    .put("id", it.id)
                    .put("nombre", it.nombre)
                    .put("autor", it.autor)
                    .put("pistas", it.pistas)
                    .put("tipo", it.tipo)
            )
        }
        prefs(c).edit().putString(CLAVE, lista.toString()).apply()
    }

    fun limpiar(c: Context) {
        prefs(c).edit().remove(CLAVE).apply()
    }
}
