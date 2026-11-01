package com.dancenot.sunov1

import android.content.ContentValues
import android.content.Context
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import java.io.File

/** Guarda el audio en Música/Suno v1 (MediaStore en Android 10+). */
object Almacen {

    val carpetaVisible: String
        get() = "Music/Suno v1"

    fun guardar(context: Context, origen: File, nombre: String): String {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val resolver = context.contentResolver
            val carpeta = "$carpetaVisible/"
            // Si ya existe una descarga con el mismo nombre, se reemplaza.
            try {
                resolver.delete(
                    MediaStore.Audio.Media.EXTERNAL_CONTENT_URI,
                    "${MediaStore.Audio.Media.DISPLAY_NAME} = ? AND " +
                        "${MediaStore.Audio.Media.RELATIVE_PATH} = ?",
                    arrayOf(nombre, carpeta),
                )
            } catch (_: Exception) {
            }
            val valores = ContentValues().apply {
                put(MediaStore.Audio.Media.DISPLAY_NAME, nombre)
                put(MediaStore.Audio.Media.MIME_TYPE, "audio/mp4")
                put(MediaStore.Audio.Media.RELATIVE_PATH, carpeta)
                put(MediaStore.Audio.Media.IS_MUSIC, 1)
            }
            val uri = resolver.insert(MediaStore.Audio.Media.EXTERNAL_CONTENT_URI, valores)
                ?: throw IllegalStateException("MediaStore rechazó el archivo")
            resolver.openOutputStream(uri)?.use { salida ->
                origen.inputStream().use { it.copyTo(salida) }
            } ?: throw IllegalStateException("no se pudo abrir el destino")
            return "$carpetaVisible/$nombre"
        }

        @Suppress("DEPRECATION")
        val destino = File(
            Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_MUSIC),
            "Suno v1"
        )
        destino.mkdirs()
        val archivo = File(destino, nombre)
        origen.inputStream().use { entrada -> archivo.outputStream().use { entrada.copyTo(it) } }
        return archivo.absolutePath
    }
}
