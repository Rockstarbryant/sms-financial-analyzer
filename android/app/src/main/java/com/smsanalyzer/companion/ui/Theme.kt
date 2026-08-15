package com.smsanalyzer.companion.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val Paper = Color(0xFFF7F3EB)
private val PaperRaised = Color(0xFFFFFCF7)
private val Ink = Color(0xFF1A1C1A)
private val InkSoft = Color(0xFF5C5F5C)
private val Mpesa = Color(0xFF0B6E3C)
private val Airtel = Color(0xFFD32F2F)
private val Line = Color(0xFFE0DBD0)

private val colors = lightColorScheme(
    primary = Mpesa,
    onPrimary = Color.White,
    secondary = InkSoft,
    background = Paper,
    surface = PaperRaised,
    onBackground = Ink,
    onSurface = Ink,
    error = Airtel,
    outline = Line,
)

@Composable
fun SmsAnalyzerTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = colors,
        content = content,
    )
}
