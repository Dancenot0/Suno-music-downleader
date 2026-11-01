package com.dancenot.sunov1

import android.Manifest
import android.content.ClipboardManager
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

const val VERSION = "1.3.0"

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Avisos.preparar(this)
        pedirPermisos()
        val enlace = intent?.getStringExtra("url")
            ?: intent?.data?.toString().orEmpty()
        val auto = intent?.getBooleanExtra("auto", false) ?: false
        setContent {
            MaterialTheme(
                colorScheme = darkColorScheme(
                    background = T.FONDO, surface = T.FONDO, primary = T.AMBAR,
                    onBackground = T.TEXTO, onSurface = T.TEXTO,
                )
            ) {
                Pantalla(enlace, auto)
            }
        }
    }

    private fun pedirPermisos() {
        val faltan = mutableListOf<String>()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            faltan.add(Manifest.permission.POST_NOTIFICATIONS)
        }
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.WRITE_EXTERNAL_STORAGE) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            faltan.add(Manifest.permission.WRITE_EXTERNAL_STORAGE)
        }
        if (faltan.isNotEmpty()) requestPermissions(faltan.toTypedArray(), 7)
    }
}

private fun mmss(segundos: Double): String {
    val total = segundos.toInt()
    val h = total / 3600
    val m = (total % 3600) / 60
    val s = total % 60
    return if (h > 0) "%d:%02d:%02d".format(h, m, s) else "%d:%02d".format(m, s)
}

private fun humanizar(bytes: Long): String = when {
    bytes >= 1024L * 1024 * 1024 -> "%.1f GB".format(bytes / (1024.0 * 1024 * 1024))
    bytes >= 1024L * 1024 -> "%.1f MB".format(bytes / (1024.0 * 1024))
    else -> "%.0f KB".format(bytes / 1024.0)
}

@Composable
private fun Pantalla(enlaceInicial: String, auto: Boolean) {
    val contexto = LocalContext.current
    val alcance = rememberCoroutineScope()

    var ajustes by remember { mutableStateOf(Ajustes.cargar(contexto)) }
    var verAjustes by remember { mutableStateOf(false) }
    var enlaces by remember { mutableStateOf(enlaceInicial) }
    var playlists by remember { mutableStateOf<List<SunoApi.Playlist>>(emptyList()) }
    var elegidos by remember { mutableStateOf<Set<String>>(emptySet()) }
    var filtro by remember { mutableStateOf("") }
    var analizando by remember { mutableStateOf(false) }
    var descargando by remember { mutableStateOf(false) }
    var motor by remember { mutableStateOf<Motor?>(null) }
    var progreso by remember { mutableStateOf(0f) }
    var mensaje by remember { mutableStateOf("Pega uno o varios enlaces de Suno.") }
    var tono by remember { mutableStateOf(T.SUAVE) }
    var detalle by remember { mutableStateOf("") }
    var registro by remember { mutableStateOf<List<String>>(emptyList()) }
    var recientes by remember { mutableStateOf(Historial.leer(contexto)) }
    var fallidas by remember { mutableStateOf<List<String>>(emptyList()) }
    var fallidasIds by remember { mutableStateOf<List<String>>(emptyList()) }
    val desplazamiento = rememberScrollState()

    fun estado(texto: String, color: Color = T.SUAVE, registrar: Boolean = true) {
        mensaje = texto
        tono = color
        if (registrar) registro = (registro + texto).takeLast(6)
    }

    fun cambiar(nuevo: Ajustes) {
        ajustes = nuevo
        Ajustes.guardar(contexto, nuevo)
    }

    fun analizar(texto: String = enlaces) {
        if (analizando || descargando) return
        if (texto.isBlank()) {
            estado("Pega un enlace de Suno.", T.ROJO)
            return
        }
        analizando = true
        estado("Consultando Suno…", registrar = false)
        alcance.launch {
            try {
                val objetivos = withContext(Dispatchers.IO) { SunoApi.leerEnlaces(texto) }
                val cargadas = mutableListOf<SunoApi.Playlist>()
                objetivos.forEachIndexed { i, objetivo ->
                    if (objetivos.size > 1) {
                        estado("Consultando ${i + 1} de ${objetivos.size}…", registrar = false)
                    }
                    cargadas += withContext(Dispatchers.IO) {
                        SunoApi.cargar(objetivo, ajustes.timeoutS)
                    }
                }
                playlists = cargadas
                elegidos = cargadas.flatMap { pl -> pl.pistas.map { it.id } }.toSet()
                fallidas = emptyList()
                progreso = 0f
                cargadas.forEach { Historial.apuntar(contexto, it) }
                recientes = Historial.leer(contexto)
                val pistas = cargadas.sumOf { it.pistas.size }
                estado("$pistas pista(s) en ${cargadas.size} lista(s).", T.VERDE)
            } catch (e: Exception) {
                estado("No se pudo: ${e.message?.take(70)}", T.ROJO)
            } finally {
                analizando = false
            }
        }
    }

    fun descargar() {
        if (descargando) return
        if (playlists.isEmpty()) {
            analizar()
            return
        }
        if (elegidos.isEmpty()) {
            estado("Marca al menos una pista.", T.ROJO)
            return
        }
        val nuevo = Motor(contexto, ajustes)
        motor = nuevo
        descargando = true
        progreso = 0f
        fallidas = emptyList()
        estado("Descargando…")

        alcance.launch {
            val resultado = nuevo.ejecutar(playlists, elegidos)
            descargando = false
            progreso = 1f
            fallidas = resultado.fallidas
            fallidasIds = resultado.fallidasIds
            val partes = mutableListOf<String>()
            if (resultado.ok > 0) partes += "${resultado.ok} descargada(s)"
            if (resultado.saltadas > 0) partes += "${resultado.saltadas} ya estaban"
            if (resultado.fallidas.isNotEmpty()) partes += "${resultado.fallidas.size} con error"
            val texto = when {
                resultado.bloqueado -> "Suno pidió calma. Espera un rato y reintenta."
                resultado.cancelado -> "Detenido. " + partes.joinToString(" · ")
                partes.isEmpty() -> "No se descargó nada."
                else -> "Listo. " + partes.joinToString(" · ")
            }
            val aviso = nuevo.ultimoAviso
            val completo = if (aviso.isNotBlank()) "$texto · $aviso" else texto
            val color = when {
                resultado.bloqueado || resultado.fallidas.isNotEmpty() -> T.ROJO
                resultado.cancelado -> T.SUAVE
                else -> T.VERDE
            }
            estado(completo, color)
            if (ajustes.notificar) Avisos.terminar(contexto, "Suno v1", completo)
        }
    }

    LaunchedEffect(descargando) {
        while (descargando) {
            motor?.let { m ->
                progreso = m.avance
                if (m.estado.isNotBlank()) detalle = m.estado
                registro = m.registro.toList().takeLast(6)
            }
            delay(250)
        }
    }

    LaunchedEffect(enlaceInicial) {
        if (enlaceInicial.isNotBlank()) analizar(enlaceInicial)
    }

    LaunchedEffect(auto, playlists) {
        if (auto && playlists.isNotEmpty() && !descargando && motor == null) descargar()
    }

    if (verAjustes) {
        PantallaAjustes(
            ajustes = ajustes,
            alCambiar = ::cambiar,
            alCerrar = { verAjustes = false },
            alBorrarHistorial = {
                Historial.limpiar(contexto)
                recientes = emptyList()
            },
        )
        return
    }

    val visibles = remember(playlists, filtro) {
        playlists.flatMap { pl ->
            pl.pistas
                .filter { filtro.isBlank() || it.titulo.contains(filtro, ignoreCase = true) }
                .map { pl to it }
        }
    }

    Box(Modifier.fillMaxSize().background(T.FONDO)) {
        Column(
            Modifier
                .fillMaxSize()
                .statusBarsPadding()
                .navigationBarsPadding()
        ) {
            Cabecera(alAjustes = { verAjustes = true })
            Column(
                Modifier
                    .weight(1f)
                    .verticalScroll(desplazamiento)
                    .padding(horizontal = 16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Tarjeta {
                    Etiqueta("ENLACES DE SUNO")
                    OutlinedTextField(
                        value = enlaces,
                        onValueChange = { enlaces = it },
                        placeholder = {
                            Text(
                                "https://suno.com/playlist/…\nUno por línea",
                                color = T.TENUE, fontSize = 13.sp
                            )
                        },
                        minLines = 2,
                        maxLines = 6,
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp),
                        textStyle = TextStyle(fontSize = 13.sp, color = T.TEXTO),
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = T.AMBAR.copy(alpha = 0.6f),
                            unfocusedBorderColor = T.BORDE,
                            focusedContainerColor = Color(0x0DFFFFFF),
                            unfocusedContainerColor = Color(0x0DFFFFFF),
                        ),
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        Boton("Pegar", variante = 1, alto = 42, modifier = Modifier.weight(1f)) {
                            val clip = (contexto.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager)
                                .primaryClip?.getItemAt(0)?.coerceToText(contexto)?.toString().orEmpty()
                            if (clip.contains("suno.com/")) {
                                enlaces = clip.trim()
                                estado("Enlace pegado.")
                            } else {
                                estado("El portapapeles no tiene un enlace de Suno.", T.ROJO)
                            }
                        }
                        Boton("Limpiar", variante = 1, alto = 42, modifier = Modifier.weight(1f)) {
                            enlaces = ""
                            playlists = emptyList()
                            elegidos = emptySet()
                            estado("Pega uno o varios enlaces de Suno.")
                        }
                    }
                }

                if (playlists.isEmpty() && recientes.isNotEmpty() && !analizando) {
                    Tarjeta {
                        Etiqueta("RECIENTES")
                        recientes.take(3).forEach { r ->
                            Row(
                                Modifier
                                    .fillMaxWidth()
                                    .clip(RoundedCornerShape(10.dp))
                                    .padding(vertical = 6.dp),
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                Column(Modifier.weight(1f)) {
                                    Text(r.nombre, color = T.TEXTO, fontSize = 14.sp, maxLines = 1)
                                    Text(
                                        "${r.autor.ifBlank { "Suno" }} · ${r.pistas} pistas",
                                        color = T.TENUE, fontSize = 11.sp
                                    )
                                }
                                Boton("Abrir", variante = 1, alto = 34) {
                                    val url = "https://suno.com/${r.tipo}/${r.id}"
                                    enlaces = url
                                    analizar(url)
                                }
                            }
                        }
                    }
                }

                playlists.forEach { pl ->
                    Tarjeta {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            var portada by remember(pl.id) {
                                mutableStateOf<android.graphics.Bitmap?>(null)
                            }
                            LaunchedEffect(pl.id) {
                                val datos = withContext(Dispatchers.IO) {
                                    SunoApi.descargarImagen(pl.portada, ajustes.timeoutS)
                                }
                                if (datos != null) {
                                    portada = android.graphics.BitmapFactory
                                        .decodeByteArray(datos, 0, datos.size)
                                }
                            }
                            Box(
                                Modifier
                                    .size(46.dp)
                                    .clip(RoundedCornerShape(12.dp))
                                    .background(
                                        Brush.linearGradient(
                                            listOf(T.AMBAR.copy(alpha = 0.85f), T.CORAL.copy(alpha = 0.8f))
                                        )
                                    )
                            ) {
                                portada?.let { mapa ->
                                    Image(
                                        bitmap = mapa.asImageBitmap(),
                                        contentDescription = null,
                                        contentScale = ContentScale.Crop,
                                        modifier = Modifier.fillMaxSize(),
                                    )
                                }
                            }
                            Spacer(Modifier.width(12.dp))
                            Column(Modifier.weight(1f)) {
                                Text(
                                    pl.nombre, color = T.TEXTO, fontSize = 16.sp,
                                    fontWeight = FontWeight.SemiBold, maxLines = 1
                                )
                                Text(
                                    "${pl.autor.ifBlank { "Suno" }} · ${pl.pistas.size} pistas · " +
                                        mmss(pl.total),
                                    color = T.TENUE, fontSize = 12.sp
                                )
                            }
                        }
                        if (pl.descripcion.isNotBlank()) Nota(pl.descripcion.take(160))
                    }
                }

                if (playlists.isNotEmpty()) {
                    Tarjeta {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Etiqueta("PISTAS")
                            Spacer(Modifier.weight(1f))
                            Text(
                                "${elegidos.size} de ${playlists.sumOf { it.pistas.size }}",
                                color = T.SUAVE, fontSize = 11.sp
                            )
                        }
                        OutlinedTextField(
                            value = filtro,
                            onValueChange = { filtro = it },
                            placeholder = { Text("Buscar en las pistas…", color = T.TENUE, fontSize = 13.sp) },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp),
                            textStyle = TextStyle(fontSize = 13.sp, color = T.TEXTO),
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedBorderColor = T.AMBAR.copy(alpha = 0.6f),
                                unfocusedBorderColor = T.BORDE,
                                focusedContainerColor = Color(0x0DFFFFFF),
                                unfocusedContainerColor = Color(0x0DFFFFFF),
                            ),
                        )
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Boton("Todo", variante = 1, alto = 36, modifier = Modifier.weight(1f)) {
                                elegidos = elegidos + visibles.map { it.second.id }
                            }
                            Boton("Nada", variante = 1, alto = 36, modifier = Modifier.weight(1f)) {
                                elegidos = elegidos - visibles.map { it.second.id }.toSet()
                            }
                            Boton("Invertir", variante = 1, alto = 36, modifier = Modifier.weight(1f)) {
                                val ids = visibles.map { it.second.id }.toSet()
                                elegidos = (elegidos - ids) + ids.filterNot { it in elegidos }
                            }
                        }
                        val varias = playlists.size > 1
                        visibles.forEach { (pl, pista) ->
                            FilaPista(
                                titulo = pista.titulo,
                                subtitulo = if (varias) pl.nombre else null,
                                duracion = pista.duracion,
                                marcado = pista.id in elegidos,
                                alCambiar = {
                                    elegidos = if (pista.id in elegidos) elegidos - pista.id
                                    else elegidos + pista.id
                                },
                            )
                        }
                        if (visibles.isEmpty()) Nota("Ninguna pista coincide con la búsqueda.")
                    }
                }

                Tarjeta {
                    Etiqueta("SALIDA")
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text(ajustes.destino, color = T.TEXTO, fontSize = 13.sp)
                            Text(
                                if (ajustes.subcarpeta) "Una subcarpeta por playlist"
                                else "Todas las pistas juntas",
                                color = T.TENUE, fontSize = 11.sp
                            )
                        }
                        Boton("Abrir", variante = 1, alto = 34) {
                            if (!Almacen.abrirCarpeta(contexto, ajustes.destino)) {
                                estado("No hay un gestor de archivos disponible.", T.ROJO)
                            }
                        }
                    }
                    Nota("Formato: M4A original de Suno, sin recomprimir. La portada y la letra van dentro del archivo.")
                    OutlinedTextField(
                        value = ajustes.plantilla,
                        onValueChange = { cambiar(ajustes.copy(plantilla = it)) },
                        label = { Text("Nombre de archivo", color = T.TENUE, fontSize = 11.sp) },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp),
                        textStyle = TextStyle(fontSize = 13.sp, color = T.TEXTO),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = T.AMBAR.copy(alpha = 0.6f),
                            unfocusedBorderColor = T.BORDE,
                            focusedContainerColor = Color(0x0DFFFFFF),
                            unfocusedContainerColor = Color(0x0DFFFFFF),
                        ),
                    )
                    Nota("{n} · {title} · {artist} · {album} · {date} · {model}")
                    Interruptor("Etiquetas", ajustes.etiquetas) {
                        cambiar(ajustes.copy(etiquetas = it))
                    }
                    Interruptor("Portada incrustada", ajustes.portada) {
                        cambiar(ajustes.copy(portada = it))
                    }
                    Interruptor("Letra incrustada", ajustes.letras) {
                        cambiar(ajustes.copy(letras = it))
                    }
                    Interruptor(
                        "Archivos aparte",
                        ajustes.aparte,
                        "Además del archivo: .lrc con la letra y .json con la ficha, en Descargas/Suno v1",
                    ) { cambiar(ajustes.copy(aparte = it)) }
                    Interruptor(
                        "Vídeo en lugar del audio",
                        ajustes.video,
                        "Descarga el MP4 de Suno cuando la pista tiene vídeo",
                    ) { cambiar(ajustes.copy(video = it)) }
                }

                Tarjeta {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Etiqueta("PROGRESO")
                        Spacer(Modifier.weight(1f))
                        Text(
                            "${(progreso * 100).toInt()}%",
                            color = T.SUAVE, fontSize = 11.sp, fontWeight = FontWeight.SemiBold
                        )
                    }
                    LinearProgressIndicator(
                        progress = { progreso },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(6.dp)
                            .clip(RoundedCornerShape(3.dp)),
                        color = T.AMBAR,
                        trackColor = Color(0x14FFFFFF),
                        drawStopIndicator = {},
                    )
                    Text(mensaje, color = tono, fontSize = 12.5.sp)
                    if (detalle.isNotBlank() && descargando) {
                        Text(detalle, color = T.SUAVE, fontSize = 11.sp, maxLines = 2)
                    }
                    if (registro.isNotEmpty()) {
                        Column(verticalArrangement = Arrangement.spacedBy(1.dp)) {
                            registro.takeLast(3).forEach {
                                Text(it, color = T.TENUE, fontSize = 10.sp, maxLines = 1)
                            }
                        }
                    }
                }

                if (fallidas.isNotEmpty() && !descargando) {
                    Tarjeta {
                        Etiqueta("FALLARON", T.ROJO)
                        fallidas.take(6).forEach {
                            Text("· $it", color = T.SUAVE, fontSize = 12.sp, maxLines = 1)
                        }
                        Boton("Reintentar fallidas", variante = 1, alto = 40) {
                            elegidos = fallidasIds.toSet()
                            fallidas = emptyList()
                            fallidasIds = emptyList()
                            descargar()
                        }
                    }
                }

                Spacer(Modifier.height(18.dp))
            }

            BarraInferior(
                descargando = descargando,
                pausado = motor?.pausado == true,
                analizando = analizando,
                hayPlaylist = playlists.isNotEmpty(),
                cuantas = elegidos.size,
                alAnalizar = { analizar() },
                alDescargar = { descargar() },
                alPausar = {
                    motor?.let {
                        it.pausar(!it.pausado)
                        estado(if (it.pausado) "En pausa." else "Reanudando…")
                    }
                },
                alDetener = { motor?.detener() },
            )
        }
    }
}

@Composable
private fun Cabecera(alAjustes: () -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .padding(start = 18.dp, end = 8.dp, top = 12.dp, bottom = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            Modifier
                .size(38.dp)
                .clip(CircleShape)
                .background(Brush.linearGradient(listOf(T.AMBAR, T.CORAL)))
        )
        Spacer(Modifier.width(12.dp))
        Column(Modifier.weight(1f)) {
            Text("Suno v1", color = T.TEXTO, fontSize = 18.sp, fontWeight = FontWeight.Bold)
            Text("móvil · $VERSION", color = T.TENUE, fontSize = 11.sp)
        }
        IconButton(onClick = alAjustes) {
            Icon(Icons.Filled.Settings, contentDescription = "Ajustes", tint = T.SUAVE)
        }
    }
}

@Composable
private fun BarraInferior(
    descargando: Boolean,
    pausado: Boolean,
    analizando: Boolean,
    hayPlaylist: Boolean,
    cuantas: Int,
    alAnalizar: () -> Unit,
    alDescargar: () -> Unit,
    alPausar: () -> Unit,
    alDetener: () -> Unit,
) {
    Column(
        Modifier
            .fillMaxWidth()
            .background(Color(0xCC08080A))
            .padding(horizontal = 16.dp, vertical = 10.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        if (descargando) {
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Boton(
                    if (pausado) "Reanudar" else "Pausar",
                    variante = 1, alto = 46, modifier = Modifier.weight(1f), alPulsar = alPausar,
                )
                Boton("Detener", variante = 2, alto = 46, modifier = Modifier.weight(1f), alPulsar = alDetener)
            }
        } else {
            Boton(
                when {
                    analizando -> "Analizando…"
                    hayPlaylist -> "Descargar ($cuantas)"
                    else -> "Analizar"
                },
                habilitado = !analizando && (!hayPlaylist || cuantas > 0),
                alto = 50,
                modifier = Modifier.fillMaxWidth(),
            ) {
                if (hayPlaylist) alDescargar() else alAnalizar()
            }
        }
    }
}

@Composable
private fun PantallaAjustes(
    ajustes: Ajustes,
    alCambiar: (Ajustes) -> Unit,
    alCerrar: () -> Unit,
    alBorrarHistorial: () -> Unit,
) {
    Column(
        Modifier
            .fillMaxSize()
            .background(T.FONDO)
            .statusBarsPadding()
            .navigationBarsPadding()
    ) {
        Row(
            Modifier
                .fillMaxWidth()
                .padding(start = 6.dp, end = 18.dp, top = 8.dp, bottom = 6.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            IconButton(onClick = alCerrar) {
                Icon(Icons.Filled.ArrowBack, contentDescription = "Volver", tint = T.TEXTO)
            }
            Column {
                Text("Ajustes", color = T.TEXTO, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                Text("Suno v1 · móvil $VERSION", color = T.TENUE, fontSize = 11.sp)
            }
        }
        Column(
            Modifier
                .weight(1f)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Tarjeta {
                Etiqueta("DESCARGA")
                Paso("Pausa entre pistas", ajustes.pausaMs / 1000, " s", 0, 10) {
                    alCambiar(ajustes.copy(pausaMs = it * 1000))
                }
                Paso("Reintentos", ajustes.reintentos, "x", 1, 5) {
                    alCambiar(ajustes.copy(reintentos = it))
                }
                Paso("Timeout", ajustes.timeoutS, " s", 15, 180) {
                    alCambiar(ajustes.copy(timeoutS = it))
                }
                Interruptor(
                    "Omitir ya descargadas", ajustes.omitir,
                    "Si el archivo ya está en la carpeta, no lo vuelve a bajar",
                ) { alCambiar(ajustes.copy(omitir = it)) }
                Interruptor(
                    "Subcarpeta por playlist", ajustes.subcarpeta,
                    "Cada playlist en su propia carpeta",
                ) { alCambiar(ajustes.copy(subcarpeta = it)) }
            }

            Tarjeta {
                Etiqueta("CARPETA")
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text(ajustes.destino, color = T.TEXTO, fontSize = 13.sp)
                    }
                    Boton("Música", variante = 1, alto = 34) {
                        alCambiar(ajustes.copy(destino = Ajustes.MUSICA))
                    }
                    Spacer(Modifier.width(8.dp))
                    Boton("Descargas", variante = 1, alto = 34) {
                        alCambiar(ajustes.copy(destino = Ajustes.DESCARGAS))
                    }
                }
                Nota("En Música, los archivos aparecen en la app de música del teléfono.")
            }

            Tarjeta {
                Etiqueta("AVISOS")
                Interruptor(
                    "Notificar al terminar", ajustes.notificar,
                    "Aviso en la barra de notificaciones cuando acaba la descarga",
                ) { alCambiar(ajustes.copy(notificar = it)) }
            }

            Tarjeta {
                Etiqueta("HISTORIAL")
                Nota("Las playlists analizadas se guardan para volver a abrirlas.")
                Boton("Borrar historial", variante = 1, alto = 40, alPulsar = alBorrarHistorial)
            }

            Tarjeta {
                Etiqueta("ACERCA DE")
                Text("Suno v1 · $VERSION", color = T.TEXTO, fontSize = 14.sp)
                Nota(
                    "Cliente libre para descargar las canciones de tu cuenta de Suno. " +
                        "Gratis, sin modificar ni redistribuir. El motor de descarga reutiliza " +
                        "el núcleo MIT de suno-dl (zarigata) con sus créditos."
                )
                Nota("Uso personal: respeta los términos de Suno y los derechos de las canciones.")
            }

            Spacer(Modifier.height(24.dp))
        }
    }
}
