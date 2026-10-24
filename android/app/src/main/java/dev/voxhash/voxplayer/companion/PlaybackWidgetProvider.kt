package dev.voxhash.voxplayer.companion

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.os.Build
import android.widget.RemoteViews

/**
 * Home-screen media controls without GMS / Glance. Talks to [PlaybackService]
 * via foreground-service intents (safe for play when the process is cold).
 */
class PlaybackWidgetProvider : AppWidgetProvider() {
    override fun onUpdate(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetIds: IntArray,
    ) {
        appWidgetIds.forEach { id ->
            appWidgetManager.updateAppWidget(id, buildViews(context, title = null, subtitle = null, playing = false))
        }
    }

    override fun onReceive(context: Context, intent: Intent) {
        when (intent.action) {
            ACTION_UPDATE -> {
                val title = intent.getStringExtra(EXTRA_TITLE)
                val subtitle = intent.getStringExtra(EXTRA_SUBTITLE)
                val playing = intent.getBooleanExtra(EXTRA_PLAYING, false)
                val mgr = AppWidgetManager.getInstance(context)
                val ids = mgr.getAppWidgetIds(ComponentName(context, PlaybackWidgetProvider::class.java))
                ids.forEach { id ->
                    mgr.updateAppWidget(id, buildViews(context, title, subtitle, playing))
                }
            }
            else -> super.onReceive(context, intent)
        }
    }

    companion object {
        const val ACTION_UPDATE = "dev.voxhash.voxplayer.WIDGET_UPDATE"
        const val ACTION_PREV = "dev.voxhash.voxplayer.WIDGET_PREV"
        const val ACTION_PLAY_PAUSE = "dev.voxhash.voxplayer.WIDGET_PLAY_PAUSE"
        const val ACTION_NEXT = "dev.voxhash.voxplayer.WIDGET_NEXT"
        const val EXTRA_TITLE = "title"
        const val EXTRA_SUBTITLE = "subtitle"
        const val EXTRA_PLAYING = "playing"

        fun notify(
            context: Context,
            title: String?,
            subtitle: String?,
            playing: Boolean,
        ) {
            context.sendBroadcast(
                Intent(ACTION_UPDATE)
                    .setPackage(context.packageName)
                    .putExtra(EXTRA_TITLE, title)
                    .putExtra(EXTRA_SUBTITLE, subtitle)
                    .putExtra(EXTRA_PLAYING, playing),
            )
        }

        fun buildViews(
            context: Context,
            title: String?,
            subtitle: String?,
            playing: Boolean,
        ): RemoteViews {
            val views = RemoteViews(context.packageName, R.layout.widget_playback)
            views.setTextViewText(
                R.id.widget_title,
                title?.takeIf { it.isNotBlank() && it != "(nothing loaded)" }
                    ?: context.getString(R.string.widget_idle),
            )
            views.setTextViewText(
                R.id.widget_subtitle,
                subtitle?.takeIf { it.isNotBlank() }
                    ?: if (playing) "Playing" else context.getString(R.string.widget_hint),
            )
            views.setImageViewResource(
                R.id.widget_play_pause,
                if (playing) android.R.drawable.ic_media_pause else android.R.drawable.ic_media_play,
            )
            views.setOnClickPendingIntent(R.id.widget_prev, servicePending(context, ACTION_PREV, 1))
            views.setOnClickPendingIntent(R.id.widget_play_pause, servicePending(context, ACTION_PLAY_PAUSE, 2, foreground = true))
            views.setOnClickPendingIntent(R.id.widget_next, servicePending(context, ACTION_NEXT, 3))
            views.setOnClickPendingIntent(
                R.id.widget_root,
                PendingIntent.getActivity(
                    context,
                    0,
                    Intent(context, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
                    pendingFlags(),
                ),
            )
            return views
        }

        private fun servicePending(
            context: Context,
            action: String,
            requestCode: Int,
            foreground: Boolean = false,
        ): PendingIntent {
            val intent = Intent(context, PlaybackService::class.java).setAction(action)
            val flags = pendingFlags()
            return if (foreground && Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                PendingIntent.getForegroundService(context, requestCode, intent, flags)
            } else {
                PendingIntent.getService(context, requestCode, intent, flags)
            }
        }

        private fun pendingFlags(): Int =
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
    }
}
