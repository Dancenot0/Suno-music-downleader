package com.dancenot.sunov1

import android.Manifest
import android.content.ClipboardManager
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

private val FONDO = Color(0xFF08080A)
private val TARJETA = Color(0x0DFFFFFF)
private val BORDE = Color(0x1AFFFFFF)
private val TEXTO = Color(0xFFF5F4F4)
private val SUAVE = Color(0xFFA8A7B0)
private val TENUE = Color(0xFF706F78)
private val AMBAR = Color(0xFFF2A94E)
private val CORAL = Color(0xFFE8705B)
private val VERDE = Color(0xFF7FCCA6)
private val ROJO = Color(0xFFE06C6C)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        pedirPermisos()
        val enlace = intent?.getStringExtra("url")
            ?: intent?.data?.toString().orEmpty()
        val auto = intent?.getBooleanExtra("auto", false) ?: false
        setContent {
            MaterialTheme(
                colorScheme = darkColorScheme(
                    background = FONDO, surface = FONDO, primary = AMBAR,
                    onBackground = TEXTO, onSurface = TEXTO,
                )
            ) {
                Pantalla(enlace, auto)
            }
        }
    }

    private fun pedirPermisos() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) {
            val permisos = mutableListOf(Manifest.permission.READ_EXTERNAL_STORAGE)
            if (Build.VERSION.SDK_INT <= Build.VERSION_CODES.P) {
                permisos.add(Manifest.permission.WRITE_EXTERNAL_STORAGE)
            }
            val faltan = permisos.filter {
                ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
            }
            if (faltan.isNotEmpty()) requestPermissions(faltan.toTypedArray(), 7)
        }
    }
}

private fun limpiar(texto: String): String =
    texto.replace(Regex("[\\\\/:*?\"<>|\\r\\n\\t]+"), " ")
        .replace(Regex("\\s+"), " ")
        .trim(' ', '.')
        .take(100)
        .ifBlank { "Sin título" }

@Composable
private fun Pantalla(enlace: String = "", auto: Boolean = false) {
    val contexto = LocalContext.current
    val alcance = rememberCoroutineScope()

    var url by remember { mutableStateOf(enlace) }
    var playlist by remember { mutableStateOf<SunoApi.Playlist?>(null) }
    var elegidos by remember { mutableStateOf<Set<String>>(emptySet()) }
    var ocupado by remember { mutableStateOf(false) }
    var descargando by remember { mutableStateOf(false) }
    var progreso by remember { mutableStateOf(0f) }
    var mensaje by remember { mutableStateOf("Pega un enlace de Suno para empezar.") }
    var tono by remember { mutableStateOf(SUAVE) }

    fun estado(texto: String, color: Color = SUAVE) {
        mensaje = texto
        tono = color
    }

    fun analizar() {
        if (ocupado || url.isBlank()) return
        ocupado = true
        estado("Consultando Suno…")
        alcance.launch {
            try {
                val id = SunoApi.idDePlaylist(url)
                val pl = withContext(Dispatchers.IO) { SunoApi.playlist(id) }
                playlist = pl
                elegidos = pl.tracks.map { it.id }.toSet()
                estado("${pl.tracks.size} pistas listas para descargar.", VERDE)
            } catch (e: Exception) {
                estado("No se pudo: ${e.message?.take(70)}", ROJO)
            } finally {
                ocupado = false
            }
        }
    }

    fun descargar() {
        val pl = playlist ?: return
        if (descargando) return
        val elegir = pl.tracks.filter { it.id in elegidos }
        if (elegir.isEmpty()) {
            estado("Marca al menos una pista.", ROJO)
            return
        }
        descargando = true
        progreso = 0f
        estado("Descargando…")
        alcance.launch {
            var hechas = 0
            var avisoEtiquetas: String? = null
            try {
                withContext(Dispatchers.IO) {
                    val cache = File(contexto.cacheDir, "suno").apply { mkdirs() }
                    elegir.forEachIndexed { indice, pista ->
                        val temporal = File(cache, "pista.m4a")
                        SunoApi.descargarAudio(pista, temporal) { texto ->
                            alcance.launch { estado("${indice + 1}/${
                                elegir.size} · $texto".take(60)) }
                        }
                        alcance.launch { estado("Etiquetas…") }
                        val portada = SunoApi.descargarImagen(pista.cover)
                        val fallo = Etiquetas.escribir(
                            temporal, pista, pl.name,
                            pl.author, indice + 1, portada
                        )
                        if (fallo != null) avisoEtiquetas = fallo
                        val nombre = "${indice + 1} - ${limpiar(pista.title)}.m4a"
                        Almacen.guardar(contexto, temporal, nombre)
                        temporal.delete()
                        hechas++
                        withContext(Dispatchers.Main) {
                            progreso = hechas.toFloat() / elegir.size
                            estado("${hechas} de ${elegir.size} · ${pista.title.take(28)}", SUAVE)
                        }
                        delay(if (indice < elegir.size - 1) 1500 else 0)
                    }
                }
                estado(
                    if (avisoEtiquetas == null) "Listo. $hechas canción(es) en ${Almacen.carpetaVisible}."
                    else "Listo ($hechas), pero sin etiquetas: ${avisoEtiquetas!!.take(50)}",
                    if (avisoEtiquetas == null) VERDE else ROJO
                )
            } catch (e: Exception) {
                estado("Se paró: ${e.message?.take(70)} ($hechas hechas)", ROJO)
            } finally {
                descargando = false
            }
        }
    }

    LaunchedEffect(enlace) {
        if (enlace.isNotBlank()) analizar()
    }

    LaunchedEffect(auto, playlist) {
        if (auto && playlist != null && !descargando) descargar()
    }

    Column(
        Modifier
            .fillMaxSize()
            .background(FONDO)
            .statusBarsPadding()
            .navigationBarsPadding()
            .padding(horizontal = 18.dp)
    ) {
        Spacer(Modifier.height(14.dp))
        Cabecera()
        Spacer(Modifier.height(14.dp))

        Tarjeta {
            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Etiqueta("ENLACE DE LA PLAYLIST")
                OutlinedTextField(
                    value = url,
                    onValueChange = { url = it },
                    placeholder = { Text("https://suno.com/playlist/…", color = TENUE, fontSize = 13.sp) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    textStyle = androidx.compose.ui.text.TextStyle(fontSize = 13.sp, color = TEXTO),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = AMBAR.copy(alpha = 0.6f),
                        unfocusedBorderColor = BORDE,
                        focusedContainerColor = Color(0x0DFFFFFF),
                        unfocusedContainerColor = Color(0x0DFFFFFF),
                    ),
                )
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Boton(
                        "Pegar",
                        secundario = true,
                        modifier = Modifier.weight(1f),
                    ) {
                        val clip = (contexto.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager)
                            .primaryClip?.getItemAt(0)?.coerceToText(contexto)?.toString().orEmpty()
                        if (clip.contains("suno.com/")) {
                            url = clip.trim()
                            estado("Enlace pegado.")
                        } else {
                            estado("El portapapeles no tiene un enlace de Suno.", ROJO)
                        }
                    }
                }
            }
        }

        Spacer(Modifier.height(12.dp))

        playlist?.let { pl ->
            var portada by remember(pl.id) { mutableStateOf<android.graphics.Bitmap?>(null) }
            LaunchedEffect(pl.id) {
                val datos = withContext(Dispatchers.IO) { SunoApi.descargarImagen(pl.cover) }
                if (datos != null) {
                    portada = android.graphics.BitmapFactory
                        .decodeByteArray(datos, 0, datos.size)
                }
            }
            Tarjeta(Modifier.weight(1f, fill = false)) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        val forma = RoundedCornerShape(12.dp)
                        Box(
                            Modifier
                                .size(44.dp)
                                .clip(forma)
                                .background(
                                    Brush.linearGradient(listOf(AMBAR.copy(alpha = 0.85f), CORAL.copy(alpha = 0.8f)))
                                )
                        ) {
                            portada?.let { mapa ->
                                androidx.compose.foundation.Image(
                                    bitmap = mapa.asImageBitmap(),
                                    contentDescription = null,
                                    contentScale = androidx.compose.ui.layout.ContentScale.Crop,
                                    modifier = Modifier.fillMaxSize(),
                                )
                            }
                        }
                        Spacer(Modifier.width(12.dp))
                        Column {
                            Text(pl.name, color = TEXTO, fontSize = 16.sp, fontWeight = FontWeight.SemiBold, maxLines = 1)
                            Text(
                                "${pl.author.ifBlank { "Suno" }} · ${pl.tracks.size} pistas",
                                color = TENUE, fontSize = 12.sp
                            )
                        }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Boton("Todo", secundario = true, compacto = true, modifier = Modifier.weight(1f)) {
                            elegidos = pl.tracks.map { it.id }.toSet()
                        }
                        Boton("Nada", secundario = true, compacto = true, modifier = Modifier.weight(1f)) {
                            elegidos = emptySet()
                        }
                    }
                    LazyColumn(Modifier.weight(1f, fill = false)) {
                        itemsIndexed(pl.tracks) { _, pista ->
                            FilaPista(
                                titulo = pista.title,
                                duracion = pista.duration,
                                marcado = pista.id in elegidos,
                                alCambiar = {
                                    elegidos = if (pista.id in elegidos) elegidos - pista.id
                                    else elegidos + pista.id
                                },
                            )
                        }
                    }
                }
            }
            Spacer(Modifier.height(10.dp))
        }

        if (progreso > 0f) {
            LinearProgressIndicator(
                progress = { progreso },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(4.dp)
                    .clip(RoundedCornerShape(2.dp)),
                color = AMBAR,
                trackColor = Color(0x14FFFFFF),
            )
            Spacer(Modifier.height(8.dp))
        }

        Text(
            mensaje,
            color = tono,
            fontSize = 12.sp,
            modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
        )

        Spacer(Modifier.height(6.dp))
        Boton(
            when {
                descargando -> "Descargando…"
                playlist != null -> "Descargar ${if (elegidos.isEmpty()) "" else "(${elegidos.size})"}"
                ocupado -> "Analizando…"
                else -> "Analizar"
            },
            habilitado = !ocupado && !descargando,
            modifier = Modifier.fillMaxWidth(),
        ) {
            if (playlist != null) descargar() else analizar()
        }
        Spacer(Modifier.height(14.dp))
    }
}

@Composable
private fun Cabecera() {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(
            Modifier
                .size(30.dp)
                .clip(CircleShape)
                .background(Brush.linearGradient(listOf(AMBAR, CORAL)))
        )
        Spacer(Modifier.width(10.dp))
        Column {
            Text("Suno v1", color = TEXTO, fontSize = 17.sp, fontWeight = FontWeight.Bold)
            Text("móvil · 1.2.1", color = TENUE, fontSize = 11.sp)
        }
    }
}

@Composable
private fun Tarjeta(modifier: Modifier = Modifier, contenido: @Composable () -> Unit) {
    Box(
        modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .background(TARJETA)
            .border(1.dp, BORDE, RoundedCornerShape(20.dp))
    ) { contenido() }
}

@Composable
private fun Etiqueta(texto: String) {
    Text(texto, color = TENUE, fontSize = 10.sp, letterSpacing = 1.sp, fontWeight = FontWeight.SemiBold)
}

@Composable
private fun Boton(
    texto: String,
    habilitado: Boolean = true,
    secundario: Boolean = false,
    compacto: Boolean = false,
    modifier: Modifier = Modifier,
    alPulsar: () -> Unit,
) {
    val forma = RoundedCornerShape(14.dp)
    Button(
        onClick = alPulsar,
        enabled = habilitado,
        shape = forma,
        modifier = modifier.height(if (compacto) 38.dp else 50.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = if (secundario) Color(0x0DFFFFFF) else AMBAR,
            contentColor = if (secundario) TEXTO else Color(0xFF20140A),
            disabledContainerColor = Color(0x0DFFFFFF),
            disabledContentColor = TENUE,
        ),
        border = if (secundario) androidx.compose.foundation.BorderStroke(1.dp, BORDE) else null,
    ) {
        Text(
            texto,
            fontSize = if (compacto) 12.sp else 15.sp,
            fontWeight = if (secundario) FontWeight.Medium else FontWeight.SemiBold,
        )
    }
}

@Composable
private fun FilaPista(
    titulo: String,
    duracion: Int,
    marcado: Boolean,
    alCambiar: () -> Unit,
) {
    Row(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(10.dp))
            .height(46.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Checkbox(
            checked = marcado,
            onCheckedChange = { alCambiar() },
            modifier = Modifier.size(38.dp),
            colors = CheckboxDefaults.colors(
                checkedColor = AMBAR,
                uncheckedColor = Color(0x38FFFFFF),
                checkmarkColor = Color(0xFF20140A),
            ),
        )
        Text(
            titulo,
            color = TEXTO,
            fontSize = 14.sp,
            maxLines = 1,
            modifier = Modifier.weight(1f)
        )
        Text(
            "${duracion / 60}:${"%02d".format(duracion % 60)}",
            color = TENUE,
            fontSize = 12.sp,
            modifier = Modifier.padding(end = 8.dp)
        )
    }
}
