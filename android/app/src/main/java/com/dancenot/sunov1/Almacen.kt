package com.dancenot.sunov1

import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import java.io.File

/** Guarda los archivos en la carpeta elegida usando MediaStore (Android 10+). */
object Almacen {

    private fun normal(carpeta: String): String =
        if (carpeta.endsWith("/")) carpeta else "$carpeta/"

    private fun existe(contexto: Context, coleccion: Uri, nombre: String, carpeta: String): Boolean {
        val seleccion = "${MediaStore.MediaColumns.DISPLAY_NAME} = ? AND " +
            "${MediaStore.MediaColumns.RELATIVE_PATH} = ? AND ${MediaStore.MediaColumns.SIZE} > 0"
        contexto.contentResolver.query(
            coleccion, arrayOf(MediaStore.MediaColumns._ID), seleccion,
            arrayOf(nombre, normal(carpeta)), null
        )?.use { c -> return c.count > 0 }
        return false
    }

    private fun borrar(contexto: Context, coleccion: Uri, nombre: String, carpeta: String) {
        try {
            contexto.contentResolver.delete(
                coleccion,
                "${MediaStore.MediaColumns.DISPLAY_NAME} = ? AND ${MediaStore.MediaColumns.RELATIVE_PATH} = ?",
                arrayOf(nombre, normal(carpeta)),
            )
        } catch (_: Exception) {
        }
    }

    private fun guardar(
        contexto: Context,
        coleccion: Uri,
        mime: String,
        origen: File,
        nombre: String,
        carpeta: String,
        esMusica: Boolean = false,
    ): String {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            borrar(contexto, coleccion, nombre, carpeta)
            val valores = ContentValues().apply {
                put(MediaStore.MediaColumns.DISPLAY_NAME, nombre)
                put(MediaStore.MediaColumns.MIME_TYPE, mime)
                put(MediaStore.MediaColumns.RELATIVE_PATH, normal(carpeta))
                if (esMusica) put(MediaStore.Audio.Media.IS_MUSIC, 1)
            }
            val uri = contexto.contentResolver.insert(coleccion, valores)
                ?: throw IllegalStateException("MediaStore rechazó el archivo")
            contexto.contentResolver.openOutputStream(uri)?.use { salida ->
                origen.inputStream().use { it.copyTo(salida) }
            } ?: throw IllegalStateException("no se pudo abrir el destino")
            return "$carpeta/$nombre"
        }

        @Suppress("DEPRECATION")
        val raiz = Environment.getExternalStoragePublicDirectory(
            if (carpeta.startsWith("Download")) Environment.DIRECTORY_DOWNLOADS
            else Environment.DIRECTORY_MUSIC
        )
        val destino = File(raiz, carpeta.substringAfter('/'))
        destino.mkdirs()
        val archivo = File(destino, nombre)
        origen.inputStream().use { entrada -> archivo.outputStream().use { entrada.copyTo(it) } }
        return archivo.absolutePath
    }

    fun existeAudio(contexto: Context, nombre: String, carpeta: String): Boolean =
        existe(contexto, MediaStore.Audio.Media.EXTERNAL_CONTENT_URI, nombre, carpeta)

    fun existeVideo(contexto: Context, nombre: String, carpeta: String): Boolean =
        existe(contexto, MediaStore.Video.Media.EXTERNAL_CONTENT_URI, nombre, carpeta)

    fun guardarAudio(contexto: Context, origen: File, nombre: String, carpeta: String): String =
        guardar(
            contexto, MediaStore.Audio.Media.EXTERNAL_CONTENT_URI, "audio/mp4",
            origen, nombre, carpeta, esMusica = true
        )

    fun guardarVideo(contexto: Context, origen: File, nombre: String, carpeta: String): String =
        guardar(
            contexto, MediaStore.Video.Media.EXTERNAL_CONTENT_URI, "video/mp4",
            origen, nombre, carpeta
        )

    /**
     * Los archivos que no son multimedia (letra `.lrc`, ficha `.json`) solo
     * pueden ir a la colección de Descargas: MediaStore no deja crearlos en
     * `Music/` desde `MediaStore.Files`.
     */
    fun guardarTexto(
        contexto: Context,
        texto: String,
        nombre: String,
        mime: String,
        carpeta: String = Ajustes.DESCARGAS,
    ): String {
        val temporal = File(contexto.cacheDir, nombre)
        temporal.writeText(texto, Charsets.UTF_8)
        val coleccion = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            MediaStore.Downloads.EXTERNAL_CONTENT_URI
        } else {
            MediaStore.Files.getContentUri("external")
        }
        return try {
            guardar(contexto, coleccion, mime, temporal, nombre, carpeta)
        } finally {
            temporal.delete()
        }
    }

    /** Abre la carpeta de descargas en el gestor de archivos del teléfono. */
    fun abrirCarpeta(contexto: Context, carpeta: String): Boolean {
        val doc = "primary:" + Uri.encode(carpeta)
        val intento = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(
                Uri.parse("content://com.android.externalstorage.documents/document/$doc"), "*/*"
            )
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        return try {
            contexto.startActivity(intento)
            true
        } catch (_: Exception) {
            try {
                contexto.startActivity(
                    Intent(Intent.ACTION_VIEW).apply {
                        type = "audio/*"
                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    }
                )
                true
            } catch (_: Exception) {
                false
            }
        }
    }
}
