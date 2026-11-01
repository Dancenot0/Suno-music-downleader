package com.dancenot.sunov1

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat

/** Aviso en la barra de notificaciones cuando termina una descarga. */
object Avisos {
    private const val CANAL = "suno_v1"

    fun preparar(contexto: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val canal = NotificationChannel(
                CANAL, "Descargas", NotificationManager.IMPORTANCE_DEFAULT
            ).apply { description = "Avisos cuando termina una descarga" }
            contexto.getSystemService(NotificationManager::class.java)
                ?.createNotificationChannel(canal)
        }
    }

    fun terminar(contexto: Context, titulo: String, texto: String) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(contexto, android.Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            return
        }
        try {
            val aviso = NotificationCompat.Builder(contexto, CANAL)
                .setSmallIcon(android.R.drawable.stat_sys_download_done)
                .setContentTitle(titulo)
                .setContentText(texto)
                .setStyle(NotificationCompat.BigTextStyle().bigText(texto))
                .setAutoCancel(true)
                .setPriority(NotificationCompat.PRIORITY_DEFAULT)
                .build()
            contexto.getSystemService(NotificationManager::class.java)
                ?.notify(1001, aviso)
        } catch (_: Exception) {
        }
    }
}
