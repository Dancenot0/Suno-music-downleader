package com.dancenot.sunov1

import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.DocumentsContract
import android.provider.MediaStore
import java.io.File

/** Guarda los archivos en la carpeta elegida usando MediaStore (Android 10+). */
object Almacen {

    private const val AUDIO = 0
    private const val VIDEO = 1
    private const val OTRO = 2

    private fun normal(carpeta: String): String =
        if (carpeta.endsWith("/")) carpeta else "$carpeta/"

    /**
     * MediaStore no deja meter audio ni vídeo en la colección de Descargas, y
     * no deja archivos que no son multimedia en `Music/`. Así que la colección
     * depende de la carpeta elegida.
     */
    private fun coleccion(carpeta: String, tipo: Int): Uri {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
            return MediaStore.Files.getContentUri("external")
        }
        if (carpeta.startsWith("Download")) {
            return MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL)
        }
        return when (tipo) {
            AUDIO -> MediaStore.Audio.Media.EXTERNAL_CONTENT_URI
            VIDEO -> MediaStore.Video.Media.EXTERNAL_CONTENT_URI
            else -> MediaStore.Downloads.EXTERNAL_CONTENT_URI
        }
    }

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
        existe(contexto, coleccion(carpeta, AUDIO), nombre, carpeta)

    /** Borra la entrada; devuelve false si sigue habiendo un archivo con ese nombre. */
    fun borrarAudio(contexto: Context, nombre: String, carpeta: String): Boolean {
        borrar(contexto, coleccion(carpeta, AUDIO), nombre, carpeta)
        return !existeAudio(contexto, nombre, carpeta)
    }

    fun existeVideo(contexto: Context, nombre: String, carpeta: String): Boolean =
        existe(contexto, coleccion(carpeta, VIDEO), nombre, carpeta)

    fun guardarAudio(contexto: Context, origen: File, nombre: String, carpeta: String): String =
        guardar(
            contexto, coleccion(carpeta, AUDIO), "audio/mp4",
            origen, nombre, carpeta, esMusica = !carpeta.startsWith("Download")
        )

    fun guardarVideo(contexto: Context, origen: File, nombre: String, carpeta: String): String =
        guardar(
            contexto, coleccion(carpeta, VIDEO), "video/mp4",
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
        return try {
            guardar(contexto, coleccion(carpeta, OTRO), mime, temporal, nombre, carpeta)
        } finally {
            temporal.delete()
        }
    }

    /** Abre la carpeta de descargas en el gestor de archivos del teléfono. */
    fun abrirCarpeta(contexto: Context, carpeta: String): Boolean {
        val proveedor = "com.android.externalstorage.documents"
        val id = Uri.encode("primary:${carpeta.trimEnd('/')}")
        val documento = Uri.parse("content://$proveedor/document/$id")
        val arbol = Uri.parse("content://$proveedor/tree/$id")
        val intentos = listOf(
            // Documentos abre la carpeta directamente si no se le pone tipo
            // ni permisos (el proveedor ya sabe leer su propia carpeta).
            Intent(Intent.ACTION_VIEW).setData(documento),
            Intent(Intent.ACTION_VIEW).setData(documento)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
            Intent(Intent.ACTION_VIEW).setData(arbol),
            // Último recurso: el selector de archivos, situado en esa carpeta.
            Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                addCategory(Intent.CATEGORY_OPENABLE)
                type = "audio/*"
                putExtra(DocumentsContract.EXTRA_INITIAL_URI, documento)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            },
        )
        for (intento in intentos) {
            try {
                contexto.startActivity(intento)
                return true
            } catch (_: Exception) {
            }
        }
        return false
    }
}
