package com.dancenot.sunov1

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/** Paleta de la app (la misma del escritorio). */
object T {
    val FONDO = Color(0xFF08080A)
    val TARJETA = Color(0x0DFFFFFF)
    val BORDE = Color(0x1AFFFFFF)
    val TEXTO = Color(0xFFF5F4F4)
    val SUAVE = Color(0xFFA8A7B0)
    val TENUE = Color(0xFF706F78)
    val AMBAR = Color(0xFFF2A94E)
    val CORAL = Color(0xFFE8705B)
    val VERDE = Color(0xFF7FCCA6)
    val ROJO = Color(0xFFE06C6C)
    val TINTA = Color(0xFF20140A)
}

@Composable
fun Tarjeta(
    modifier: Modifier = Modifier,
    contenido: @Composable ColumnScope.() -> Unit,
) {
    Column(
        modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .background(T.TARJETA)
            .border(1.dp, T.BORDE, RoundedCornerShape(20.dp))
            .padding(14.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
        content = contenido,
    )
}

@Composable
fun Etiqueta(texto: String, color: Color = T.TENUE) {
    Text(
        texto,
        color = color,
        fontSize = 10.sp,
        letterSpacing = 1.sp,
        fontWeight = FontWeight.SemiBold,
    )
}

@Composable
fun Titulo(texto: String, tamano: Int = 13) {
    Text(texto, color = T.TEXTO, fontSize = tamano.sp, fontWeight = FontWeight.SemiBold)
}

@Composable
fun Nota(texto: String) {
    Text(texto, color = T.TENUE, fontSize = 11.sp, lineHeight = 15.sp)
}

@Composable
fun Boton(
    texto: String,
    modifier: Modifier = Modifier,
    habilitado: Boolean = true,
    variante: Int = 0,
    alto: Int = 50,
    alPulsar: () -> Unit,
) {
    val fondo = when (variante) {
        2 -> Color(0x26E06C6C)
        1 -> Color(0x0DFFFFFF)
        else -> T.AMBAR
    }
    val textoColor = when (variante) {
        2 -> Color(0xFFFFD9D9)
        1 -> T.TEXTO
        else -> T.TINTA
    }
    Button(
        onClick = alPulsar,
        enabled = habilitado,
        shape = RoundedCornerShape(14.dp),
        modifier = modifier.height(alto.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = fondo,
            contentColor = textoColor,
            disabledContainerColor = Color(0x0DFFFFFF),
            disabledContentColor = T.TENUE,
        ),
        border = if (variante == 0) null else BorderStroke(1.dp, T.BORDE),
    ) {
        Text(
            texto,
            fontSize = if (alto <= 40) 12.sp else 15.sp,
            fontWeight = if (variante == 0) FontWeight.SemiBold else FontWeight.Medium,
        )
    }
}

@Composable
fun Interruptor(
    titulo: String,
    activo: Boolean,
    descripcion: String? = null,
    alCambiar: (Boolean) -> Unit,
) {
    Row(
        Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(titulo, color = T.TEXTO, fontSize = 14.sp)
            descripcion?.let {
                Text(it, color = T.TENUE, fontSize = 11.sp, lineHeight = 14.sp)
            }
        }
        Spacer(Modifier.width(10.dp))
        Switch(
            checked = activo,
            onCheckedChange = alCambiar,
            colors = SwitchDefaults.colors(
                checkedThumbColor = T.TINTA,
                checkedTrackColor = T.AMBAR,
                uncheckedThumbColor = T.SUAVE,
                uncheckedTrackColor = Color(0x1FFFFFFF),
            ),
        )
    }
}

@Composable
fun Paso(
    titulo: String,
    valor: Int,
    sufijo: String,
    minimo: Int,
    maximo: Int,
    alCambiar: (Int) -> Unit,
) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(titulo, color = T.TEXTO, fontSize = 14.sp, modifier = Modifier.weight(1f))
        Boton("-", habilitado = valor > minimo, variante = 1, alto = 34) {
            alCambiar((valor - 1).coerceAtLeast(minimo))
        }
        Text(
            "$valor$sufijo",
            color = T.TEXTO,
            fontSize = 14.sp,
            fontWeight = FontWeight.SemiBold,
            modifier = Modifier.width(58.dp),
            textAlign = androidx.compose.ui.text.style.TextAlign.Center,
        )
        Boton("+", habilitado = valor < maximo, variante = 1, alto = 34) {
            alCambiar((valor + 1).coerceAtMost(maximo))
        }
    }
}

@Composable
fun FilaPista(
    titulo: String,
    subtitulo: String?,
    duracion: Int,
    marcado: Boolean,
    alCambiar: () -> Unit,
) {
    Row(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(10.dp))
            .clickable { alCambiar() }
            .padding(vertical = 2.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Checkbox(
            checked = marcado,
            onCheckedChange = { alCambiar() },
            modifier = Modifier.size(38.dp),
            colors = CheckboxDefaults.colors(
                checkedColor = T.AMBAR,
                uncheckedColor = Color(0x38FFFFFF),
                checkmarkColor = T.TINTA,
            ),
        )
        Column(Modifier.weight(1f)) {
            Text(titulo, color = T.TEXTO, fontSize = 14.sp, maxLines = 1)
            subtitulo?.let {
                Text(it, color = T.TENUE, fontSize = 10.5.sp, maxLines = 1)
            }
        }
        Text(
            "${duracion / 60}:${"%02d".format(duracion % 60)}",
            color = T.TENUE,
            fontSize = 12.sp,
            modifier = Modifier.padding(start = 8.dp),
        )
    }
}

@Composable
fun Punto(color: Color, tamano: Int = 8) {
    Box(Modifier.size(tamano.dp).clip(RoundedCornerShape(50)).background(color))
}
