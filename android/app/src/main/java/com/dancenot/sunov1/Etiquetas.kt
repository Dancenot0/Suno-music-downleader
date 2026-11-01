package com.dancenot.sunov1

import org.jaudiotagger.audio.mp4.Mp4TagReader
import org.jaudiotagger.audio.mp4.Mp4TagWriter
import org.jaudiotagger.tag.FieldKey
import org.jaudiotagger.tag.images.ArtworkFactory
import org.jaudiotagger.tag.mp4.Mp4Tag
import java.io.File
import java.io.RandomAccessFile

/**
 * Etiquetas, portada y letra DENTRO del archivo (M4A / MP4).
 *
 * El audio de Suno es Opus dentro de un contenedor MP4, y el lector de
 * cabeceras de jaudiotagger no entiende `dOps`, así que no se usa
 * `AudioFileIO.read`: se lee y escribe directamente el bloque de etiquetas.
 */
object Etiquetas {

    fun escribir(
        archivo: File,
        track: SunoApi.Track,
        album: String,
        artista: String,
        numero: Int,
        portada: ByteArray?,
    ): String? {
        val temporal = File(archivo.parentFile, archivo.name + ".tags")
        try {
            val original = RandomAccessFile(archivo, "rw")
            var tag: Mp4Tag? = null
            try {
                tag = Mp4TagReader().read(original)
            } catch (_: Exception) {
                tag = null
            }
            val etiqueta = tag ?: Mp4Tag()

            etiqueta.setField(FieldKey.TITLE, track.title)
            etiqueta.setField(FieldKey.ARTIST, artista.ifBlank { "Suno" })
            etiqueta.setField(FieldKey.ALBUM, album)
            if (track.genre.isNotBlank()) etiqueta.setField(FieldKey.GENRE, track.genre)
            if (track.created.isNotBlank()) {
                etiqueta.setField(FieldKey.YEAR, track.created.take(4))
            }
            etiqueta.setField(FieldKey.TRACK, numero.toString())
            etiqueta.setField(
                FieldKey.COMMENT,
                listOfNotNull("Generado con Suno", track.model.takeIf { it.isNotBlank() }?.let { "modelo $it" })
                    .joinToString(" · ")
            )
            if (track.lyrics.isNotBlank()) {
                try {
                    etiqueta.setField(FieldKey.LYRICS, track.lyrics)
                } catch (_: Exception) {
                }
            }
            if (portada != null) {
                val imagen = File(archivo.parentFile, archivo.name + ".jpg")
                try {
                    imagen.writeBytes(portada)
                    etiqueta.setField(ArtworkFactory.createArtworkFromFile(imagen))
                } catch (_: Exception) {
                } finally {
                    imagen.delete()
                }
            }

            val salida = RandomAccessFile(temporal, "rw")
            try {
                Mp4TagWriter().write(etiqueta, original, salida)
            } finally {
                salida.close()
                original.close()
            }

            if (temporal.length() > 1024) {
                if (!archivo.delete()) return "no se pudo reemplazar el archivo"
                if (!temporal.renameTo(archivo)) return "no se pudo renombrar el archivo"
            }
            return null
        } catch (e: Exception) {
            temporal.delete()
            return e.message ?: e.javaClass.simpleName
        }
    }
}
