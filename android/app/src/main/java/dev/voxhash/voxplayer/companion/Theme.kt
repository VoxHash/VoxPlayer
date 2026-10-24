package dev.voxhash.voxplayer.companion

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/**
 * Desktop ember-on-charcoal identity (matches ``voxplayer.theme`` _EMBER).
 * No streaming-green accents — warm ember for primary actions.
 */
object VoxColors {
    val BgApp = Color(0xFF0B0F14)
    val BgPanel = Color(0xFF121820)
    val BgElevated = Color(0xFF1A2330)
    val BgHover = Color(0xFF243044)
    val BgInput = Color(0xFF0F141C)
    val Border = Color(0xFF6A7588)
    val BorderSoft = Color(0xFF4A5568)
    val Text = Color(0xFFF2F4F7)
    val TextSecondary = Color(0xFFB0BBCB)
    val TextMuted = Color(0xFF8A96A8)
    val Accent = Color(0xFFFF8A3D)
    val AccentHover = Color(0xFFFFB070)
    val AccentPressed = Color(0xFFE06E28)
    val AccentSoft = Color(0x38FF8A3D)
    val Focus = Color(0xFF3DDCFF)
    val Danger = Color(0xFFFF6B6B)
    val Success = Color(0xFF5AD67D)
    val Transport = Color(0xFF0E141C)
    val Rail = Color(0xFF0D1219)
}

object VoxShapes {
    val card = RoundedCornerShape(12.dp)
    val panel = RoundedCornerShape(16.dp)
    val pill = RoundedCornerShape(20.dp)
    val art = RoundedCornerShape(10.dp)
}

val VoxTypography = Typography(
    displaySmall = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.SemiBold,
        fontSize = 28.sp,
        letterSpacing = (-0.3).sp,
        color = VoxColors.Text,
    ),
    headlineMedium = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.SemiBold,
        fontSize = 22.sp,
        color = VoxColors.Text,
    ),
    headlineSmall = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.SemiBold,
        fontSize = 18.sp,
        color = VoxColors.Text,
    ),
    titleMedium = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.SemiBold,
        fontSize = 15.sp,
        color = VoxColors.Text,
    ),
    bodyLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Normal,
        fontSize = 15.sp,
        color = VoxColors.Text,
    ),
    bodyMedium = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Normal,
        fontSize = 13.sp,
        color = VoxColors.TextSecondary,
    ),
    bodySmall = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Normal,
        fontSize = 12.sp,
        color = VoxColors.TextMuted,
    ),
    labelLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Medium,
        fontSize = 13.sp,
        color = VoxColors.Text,
    ),
)

fun voxColorScheme() = darkColorScheme(
    primary = VoxColors.Accent,
    onPrimary = VoxColors.BgApp,
    secondary = VoxColors.AccentHover,
    background = VoxColors.BgApp,
    surface = VoxColors.BgPanel,
    surfaceVariant = VoxColors.BgElevated,
    onBackground = VoxColors.Text,
    onSurface = VoxColors.Text,
    onSurfaceVariant = VoxColors.TextSecondary,
    outline = VoxColors.BorderSoft,
    error = VoxColors.Danger,
)

/** Quest / tablet shell when width is at least this (Meta default panel is 1024dp). */
const val WIDE_SHELL_MIN_DP = 700

/** Landscape car / dash layout without GMS Auto (wide + landscape). */
const val CAR_SHELL_MIN_DP = 900

@Composable
fun VoxTheme(content: @Composable () -> Unit) {
    androidx.compose.material3.MaterialTheme(
        colorScheme = voxColorScheme(),
        typography = VoxTypography,
        content = content,
    )
}
