package com.dancenot.sunov1

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
import android.net.Uri
import android.os.Build
import android.provider.Settings
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

/**
 * Actualizaciones como en la Play Store: la app mira el canal, se baja el
 * `.apk` nuevo y se lo pasa al instalador del sistema. Android pide una
 * confirmación la primera vez (o siempre, según el teléfono), pero ya no hay
 * que buscar el archivo ni abrirlo a mano.
 */
object Actualizador {

    private const val CANAL = "https://dancenot0.github.io/Suno-music-downleader/version.json"

    data class Nueva(val version: String, val url: String, val notas: String)

    private fun tupla(texto: String): List<Int> =
        texto.trim().split(".", "-", "+").mapNotNull { it.toIntOrNull() }.ifEmpty { listOf(0) }

    fun masNueva(candidata: String, actual: String): Boolean {
        val a = tupla(candidata)
        val b = tupla(actual)
        for (i in 0 until maxOf(a.size, b.size)) {
            val x = a.getOrElse(i) { 0 }
            val y = b.getOrElse(i) { 0 }
            if (x != y) return x > y
        }
        return false
    }

    suspend fun buscar(): Nueva? = withContext(Dispatchers.IO) {
        try {
            val conexion = URL(CANAL).openConnection() as HttpURLConnection
            conexion.connectTimeout = 12000
            conexion.readTimeout = 15000
            conexion.setRequestProperty("User-Agent", "SunoV1/$VERSION")
            val texto = conexion.inputStream.bufferedReader().readText()
            conexion.disconnect()
            val datos = JSONObject(texto)
            val android = datos.optJSONObject("android") ?: return@withContext null
            val version = android.optString("version")
            val url = android.optString("url")
            if (version.isBlank() || url.isBlank()) return@withContext null
            if (!masNueva(version, VERSION)) return@withContext null
            Nueva(version, url, android.optString("notes"))
        } catch (_: Exception) {
            null
        }
    }

    fun puedeInstalar(contexto: Context): Boolean =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            contexto.packageManager.canRequestPackageInstalls()
        } else {
            true
        }

    /** Pantalla del sistema para permitir instalar apps desde esta app. */
    fun pedirPermiso(contexto: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            try {
                contexto.startActivity(
                    Intent(
                        Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                        Uri.parse("package:${contexto.packageName}"),
                    ).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                )
            } catch (_: Exception) {
            }
        }
    }

    /** Baja el APK y lo entrega al instalador. La app se reinicia sola al acabar. */
    suspend fun instalar(
        contexto: Context,
        nueva: Nueva,
        alProgreso: (Int) -> Unit = {},
    ): String? = withContext(Dispatchers.IO) {
        try {
            val apk = File(contexto.cacheDir, "suno-${nueva.version}.apk")
            val conexion = URL(nueva.url).openConnection() as HttpURLConnection
            conexion.connectTimeout = 15000
            conexion.readTimeout = 60000
            conexion.setRequestProperty("User-Agent", "SunoV1/$VERSION")
            conexion.instanceFollowRedirects = true
            val codigo = conexion.responseCode
            if (codigo !in 200..299) return@withContext "el servidor respondió $codigo"
            val total = conexion.contentLength.toLong()
            var escrito = 0L
            conexion.inputStream.use { entrada ->
                apk.outputStream().use { salida ->
                    val buffer = ByteArray(64 * 1024)
                    while (true) {
                        val n = entrada.read(buffer)
                        if (n <= 0) break
                        salida.write(buffer, 0, n)
                        escrito += n
                        if (total > 0) alProgreso((escrito * 100 / total).toInt())
                    }
                }
            }
            conexion.disconnect()
            if (escrito < 1024) return@withContext "la descarga quedó vacía"

            val instalador = contexto.packageManager.packageInstaller
            val parametros = PackageInstaller.SessionParams(
                PackageInstaller.SessionParams.MODE_FULL_INSTALL
            ).apply {
                setAppPackageName(contexto.packageName)
                setSize(apk.length())
                try {
                    // Actualización de la propia app: sin diálogo extra.
                    setRequireUserAction(PackageInstaller.SessionParams.USER_ACTION_NOT_REQUIRED)
                } catch (_: Exception) {
                }
            }
            val sesionId = instalador.createSession(parametros)
            instalador.openSession(sesionId).use { sesion ->
                sesion.openWrite("base.apk", 0, apk.length()).use { destino ->
                    apk.inputStream().use { it.copyTo(destino) }
                }
                val aviso = Intent(contexto, InstaladorReceptor::class.java)
                    .setAction(InstaladorReceptor.ACCION)
                val banderas = PendingIntent.FLAG_UPDATE_CURRENT or
                    (if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) PendingIntent.FLAG_MUTABLE else 0)
                val pendiente = PendingIntent.getBroadcast(
                    contexto, sesionId, aviso, banderas
                )
                sesion.commit(pendiente.intentSender)
            }
            apk.delete()

            // Android cierra la app al reemplazarla. Esta alarma la vuelve a
            // abrir un rato después, ya actualizada.
            try {
                val abrir = PendingIntent.getActivity(
                    contexto,
                    42,
                    Intent(contexto, MainActivity::class.java)
                        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                        .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP),
                    PendingIntent.FLAG_UPDATE_CURRENT or
                        (if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) PendingIntent.FLAG_IMMUTABLE else 0),
                )
                val alarmas = contexto.getSystemService(android.app.AlarmManager::class.java)
                alarmas?.set(
                    android.app.AlarmManager.ELAPSED_REALTIME_WAKEUP,
                    android.os.SystemClock.elapsedRealtime() + 14_000,
                    abrir,
                )
            } catch (_: Exception) {
            }
            null
        } catch (e: Exception) {
            e.message ?: e.javaClass.simpleName
        }
    }
}

/** Recoge el resultado del instalador del sistema. */
class InstaladorReceptor : BroadcastReceiver() {
    companion object {
        const val ACCION = "com.dancenot.sunov1.INSTALADO"
    }

    override fun onReceive(contexto: Context, intent: Intent) {
        val estado = intent.getIntExtra(PackageInstaller.EXTRA_STATUS, -1)
        if (estado == PackageInstaller.STATUS_PENDING_USER_ACTION) {
            @Suppress("DEPRECATION")
            val confirmacion = intent.getParcelableExtra<Intent>(Intent.EXTRA_INTENT)
            confirmacion?.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            try {
                if (confirmacion != null) contexto.startActivity(confirmacion)
            } catch (_: Exception) {
            }
        }
    }
}
