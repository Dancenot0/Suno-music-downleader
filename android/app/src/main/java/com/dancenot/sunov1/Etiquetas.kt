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
 * El audio de Suno es Opus dentro de un contenedor MP4 y el lector de cabeceras
 * de jaudiotagger no entiende `dOps`, así que no se usa `AudioFileIO.read`:
 * se lee y escribe directamente el bloque de etiquetas.
 */
object Etiquetas {

    fun escribir(
        archivo: File,
        track: SunoApi.Track,
        album: String,
        artista: String,
        numero: Int,
        portada: ByteArray?,
        conEtiquetas: Boolean,
        conPortada: Boolean,
        conLetra: Boolean,
    ): String? {
        if (!conEtiquetas && !conPortada && !conLetra) return null
        val temporal = File(archivo.parentFile, archivo.name + ".tags")
        try {
            val original = RandomAccessFile(archivo, "rw")
            val etiqueta: Mp4Tag = try {
                Mp4TagReader().read(original) ?: Mp4Tag()
            } catch (_: Exception) {
                Mp4Tag()
            }

            if (conEtiquetas) {
                etiqueta.setField(FieldKey.TITLE, track.titulo)
                etiqueta.setField(FieldKey.ARTIST, artista.ifBlank { "Suno" })
                etiqueta.setField(FieldKey.ALBUM, album)
                if (track.genero.isNotBlank()) etiqueta.setField(FieldKey.GENRE, track.genero)
                if (track.fecha.isNotBlank()) etiqueta.setField(FieldKey.YEAR, track.fecha.take(4))
                etiqueta.setField(FieldKey.TRACK, numero.toString())
                etiqueta.setField(
                    FieldKey.COMMENT,
                    listOfNotNull(
                        "Generado con Suno",
                        track.modelo.takeIf { it.isNotBlank() }?.let { "modelo $it" }
                    ).joinToString(" · ")
                )
            }
            if (conLetra && track.letra.isNotBlank()) {
                try {
                    etiqueta.setField(FieldKey.LYRICS, track.letra)
                } catch (_: Exception) {
                }
            }
            if (conPortada && portada != null) {
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
