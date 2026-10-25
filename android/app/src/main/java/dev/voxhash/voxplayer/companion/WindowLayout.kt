package dev.voxhash.voxplayer.companion

import android.app.Activity
import android.content.Context
import android.content.ContextWrapper
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.window.layout.FoldingFeature
import androidx.window.layout.WindowInfoTracker
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

/**
 * Quest panel / foldable / multi-window snapshot (Jetpack WindowManager — no GMS).
 */
data class WindowLayoutState(
    val multiWindow: Boolean = false,
    /** True when a hinge/fold separates the usable area (tabletop / book). */
    val foldSeparating: Boolean = false,
    val foldOccluding: Boolean = false,
)

fun Context.findActivity(): Activity? {
    var ctx: Context? = this
    while (ctx is ContextWrapper) {
        if (ctx is Activity) return ctx
        ctx = ctx.baseContext
    }
    return null
}

@Composable
fun rememberWindowLayoutState(): WindowLayoutState {
    val context = LocalContext.current
    val activity = remember(context) { context.findActivity() }
    var state by remember { mutableStateOf(WindowLayoutState()) }
    val lifecycleOwner = LocalLifecycleOwner.current

    DisposableEffect(activity, lifecycleOwner) {
        if (activity == null) {
            return@DisposableEffect onDispose { }
        }
        fun refreshMultiWindow() {
            state = state.copy(multiWindow = activity.isInMultiWindowMode)
        }
        refreshMultiWindow()
        val lifecycleObserver = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME || event == Lifecycle.Event.ON_START) {
                refreshMultiWindow()
            }
        }
        lifecycleOwner.lifecycle.addObserver(lifecycleObserver)

        val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
        scope.launch {
            WindowInfoTracker.getOrCreate(activity)
                .windowLayoutInfo(activity)
                .collect { info ->
                    val folds = info.displayFeatures.filterIsInstance<FoldingFeature>()
                    state = state.copy(
                        multiWindow = activity.isInMultiWindowMode,
                        foldSeparating = folds.any { it.isSeparating },
                        foldOccluding = folds.any {
                            it.occlusionType == FoldingFeature.OcclusionType.FULL
                        },
                    )
                }
        }
        onDispose {
            lifecycleOwner.lifecycle.removeObserver(lifecycleObserver)
            scope.cancel()
        }
    }

    return state
}
