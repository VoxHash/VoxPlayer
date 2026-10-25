package dev.voxhash.voxplayer.companion

import android.content.Context
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.util.concurrent.atomic.AtomicReference

/**
 * Ember accent on charcoal (dark) or warm ink-on-paper (light).
 * Avoids generic purple / cream AI default looks. FOSS-only theming.
 */
data class VoxPalette(
    val BgApp: Color,
    val BgPanel: Color,
    val BgElevated: Color,
    val BgHover: Color,
    val BgInput: Color,
    val Border: Color,
    val BorderSoft: Color,
    val Text: Color,
    val TextSecondary: Color,
    val TextMuted: Color,
    val Accent: Color,
    val AccentHover: Color,
    val AccentPressed: Color,
    val AccentSoft: Color,
    val Focus: Color,
    val Danger: Color,
    val Success: Color,
    val Transport: Color,
    val Rail: Color,
    val dark: Boolean,
) {
    companion object {
        val Dark = VoxPalette(
            BgApp = Color(0xFF0B0F14),
            BgPanel = Color(0xFF121820),
            BgElevated = Color(0xFF1A2330),
            BgHover = Color(0xFF243044),
            BgInput = Color(0xFF0F141C),
            Border = Color(0xFF6A7588),
            BorderSoft = Color(0xFF4A5568),
            Text = Color(0xFFF2F4F7),
            TextSecondary = Color(0xFFB0BBCB),
            TextMuted = Color(0xFF8A96A8),
            Accent = Color(0xFFFF8A3D),
            AccentHover = Color(0xFFFFB070),
            AccentPressed = Color(0xFFE06E28),
            AccentSoft = Color(0x38FF8A3D),
            Focus = Color(0xFF3DDCFF),
            Danger = Color(0xFFFF6B6B),
            Success = Color(0xFF5AD67D),
            Transport = Color(0xFF0E141C),
            Rail = Color(0xFF0D1219),
            dark = true,
        )

        /** Daytime companion: slate ink + ember on warm paper (not cream/terracotta stock). */
        val Light = VoxPalette(
            BgApp = Color(0xFFF3F5F8),
            BgPanel = Color(0xFFE8ECF1),
            BgElevated = Color(0xFFFFFFFF),
            BgHover = Color(0xFFDCE3EC),
            BgInput = Color(0xFFF7F9FB),
            Border = Color(0xFF6B7788),
            BorderSoft = Color(0xFFA8B3C2),
            Text = Color(0xFF141A22),
            TextSecondary = Color(0xFF3E4A5A),
            TextMuted = Color(0xFF5C6A7C),
            Accent = Color(0xFFE06A20),
            AccentHover = Color(0xFFF08A45),
            AccentPressed = Color(0xFFC45612),
            AccentSoft = Color(0x33E06A20),
            Focus = Color(0xFF0088AA),
            Danger = Color(0xFFC62828),
            Success = Color(0xFF2E7D4F),
            Transport = Color(0xFFE2E7EE),
            Rail = Color(0xFFDDE3EB),
            dark = false,
        )
    }
}

enum class ThemeMode {
    Dark,
    Light,
    System,
    ;

    fun label(): String = when (this) {
        Dark -> "Dark"
        Light -> "Light"
        System -> "System"
    }

    companion object {
        fun fromStorage(raw: String?): ThemeMode = when (raw?.lowercase()) {
            "light" -> Light
            "system" -> System
            else -> Dark
        }
    }
}

object ThemePrefs {
    private const val PREFS = "voxplayer_theme"
    private const val KEY = "mode"

    fun load(context: Context): ThemeMode =
        ThemeMode.fromStorage(
            context.applicationContext
                .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .getString(KEY, "dark"),
        )

    fun save(context: Context, mode: ThemeMode) {
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(
                KEY,
                when (mode) {
                    ThemeMode.Dark -> "dark"
                    ThemeMode.Light -> "light"
                    ThemeMode.System -> "system"
                },
            )
            .apply()
    }

    fun resolveDark(mode: ThemeMode, systemDark: Boolean): Boolean = when (mode) {
        ThemeMode.Dark -> true
        ThemeMode.Light -> false
        ThemeMode.System -> systemDark
    }
}

/**
 * Desktop ember-on-charcoal identity (matches ``voxplayer.theme`` _EMBER).
 * Active palette swaps when [VoxTheme] applies dark/light — call sites keep
 * reading [VoxColors] properties.
 */
object VoxColors {
    private val active = AtomicReference(VoxPalette.Dark)

    fun applyPalette(palette: VoxPalette) {
        active.set(palette)
    }

    fun palette(): VoxPalette = active.get()

    val BgApp: Color get() = palette().BgApp
    val BgPanel: Color get() = palette().BgPanel
    val BgElevated: Color get() = palette().BgElevated
    val BgHover: Color get() = palette().BgHover
    val BgInput: Color get() = palette().BgInput
    val Border: Color get() = palette().Border
    val BorderSoft: Color get() = palette().BorderSoft
    val Text: Color get() = palette().Text
    val TextSecondary: Color get() = palette().TextSecondary
    val TextMuted: Color get() = palette().TextMuted
    val Accent: Color get() = palette().Accent
    val AccentHover: Color get() = palette().AccentHover
    val AccentPressed: Color get() = palette().AccentPressed
    val AccentSoft: Color get() = palette().AccentSoft
    val Focus: Color get() = palette().Focus
    val Danger: Color get() = palette().Danger
    val Success: Color get() = palette().Success
    val Transport: Color get() = palette().Transport
    val Rail: Color get() = palette().Rail
}

object VoxShapes {
    val card = RoundedCornerShape(12.dp)
    val panel = RoundedCornerShape(16.dp)
    val pill = RoundedCornerShape(20.dp)
    val art = RoundedCornerShape(10.dp)
}

val LocalVoxPalette = staticCompositionLocalOf { VoxPalette.Dark }

fun voxTypography(palette: VoxPalette) = Typography(
    displaySmall = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.SemiBold,
        fontSize = 28.sp,
        letterSpacing = (-0.3).sp,
        color = palette.Text,
    ),
    headlineMedium = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.SemiBold,
        fontSize = 22.sp,
        color = palette.Text,
    ),
    headlineSmall = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.SemiBold,
        fontSize = 18.sp,
        color = palette.Text,
    ),
    titleMedium = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.SemiBold,
        fontSize = 15.sp,
        color = palette.Text,
    ),
    bodyLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Normal,
        fontSize = 15.sp,
        color = palette.Text,
    ),
    bodyMedium = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Normal,
        fontSize = 13.sp,
        color = palette.TextSecondary,
    ),
    bodySmall = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Normal,
        fontSize = 12.sp,
        color = palette.TextMuted,
    ),
    labelLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Medium,
        fontSize = 13.sp,
        color = palette.Text,
    ),
)

/** @deprecated Prefer [voxTypography] with active palette; kept for call sites. */
val VoxTypography: Typography
    get() = voxTypography(VoxColors.palette())

fun voxColorScheme(palette: VoxPalette) = if (palette.dark) {
    darkColorScheme(
        primary = palette.Accent,
        onPrimary = palette.BgApp,
        secondary = palette.AccentHover,
        background = palette.BgApp,
        surface = palette.BgPanel,
        surfaceVariant = palette.BgElevated,
        onBackground = palette.Text,
        onSurface = palette.Text,
        onSurfaceVariant = palette.TextSecondary,
        outline = palette.BorderSoft,
        error = palette.Danger,
    )
} else {
    lightColorScheme(
        primary = palette.Accent,
        onPrimary = Color.White,
        secondary = palette.AccentHover,
        background = palette.BgApp,
        surface = palette.BgPanel,
        surfaceVariant = palette.BgElevated,
        onBackground = palette.Text,
        onSurface = palette.Text,
        onSurfaceVariant = palette.TextSecondary,
        outline = palette.BorderSoft,
        error = palette.Danger,
    )
}

fun voxColorScheme() = voxColorScheme(VoxColors.palette())

/** Quest / tablet shell when width is at least this (Meta default panel is 1024dp). */
const val WIDE_SHELL_MIN_DP = 700

/** Landscape car / dash layout without GMS Auto (wide + landscape). */
const val CAR_SHELL_MIN_DP = 900

/**
 * Quest 2D panel / multi-window strip: when window height is below this, use a
 * compact shell (hide tall chrome) so transport + library stay usable.
 */
const val PANEL_COMPACT_MAX_HEIGHT_DP = 520

@Composable
fun VoxTheme(
    mode: ThemeMode = ThemeMode.Dark,
    content: @Composable () -> Unit,
) {
    val systemDark = isSystemInDarkTheme()
    val dark = ThemePrefs.resolveDark(mode, systemDark)
    val palette = if (dark) VoxPalette.Dark else VoxPalette.Light
    VoxColors.applyPalette(palette)
    CompositionLocalProvider(LocalVoxPalette provides palette) {
        androidx.compose.material3.MaterialTheme(
            colorScheme = voxColorScheme(palette),
            typography = voxTypography(palette),
            content = content,
        )
    }
}

@Composable
@ReadOnlyComposable
fun voxPalette(): VoxPalette = LocalVoxPalette.current
