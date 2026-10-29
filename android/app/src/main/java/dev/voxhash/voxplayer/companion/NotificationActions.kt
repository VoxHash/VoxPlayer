package dev.voxhash.voxplayer.companion

import android.os.Bundle
import androidx.media3.session.SessionCommand

/**
 * Custom media-notification / System UI session commands (no GMS).
 * Wired through [PlaybackService] media-button preferences overflow slots.
 */
object NotificationActions {
    const val ACTION_BOOKMARK = "dev.voxhash.voxplayer.NOTIF_BOOKMARK"
    val CMD_BOOKMARK: SessionCommand = SessionCommand(ACTION_BOOKMARK, Bundle.EMPTY)

    const val ACTION_CYCLE_SPEED = "dev.voxhash.voxplayer.NOTIF_CYCLE_SPEED"
    val CMD_CYCLE_SPEED: SessionCommand = SessionCommand(ACTION_CYCLE_SPEED, Bundle.EMPTY)

    /** FOSS DLNA cast from the system media controls (no Google Cast / GMS). */
    const val ACTION_CAST = "dev.voxhash.voxplayer.NOTIF_CAST"
    val CMD_CAST: SessionCommand = SessionCommand(ACTION_CAST, Bundle.EMPTY)

    /** Offline Now Playing share card (FileProvider chooser — no cloud). */
    const val ACTION_SHARE = "dev.voxhash.voxplayer.NOTIF_SHARE"
    val CMD_SHARE: SessionCommand = SessionCommand(ACTION_SHARE, Bundle.EMPTY)

    /** Broadcast after notification bookmark so the UI refreshes favorites. */
    const val ACTION_BOOKMARK_SAVED = "dev.voxhash.voxplayer.BOOKMARK_SAVED"

    /** Broadcast so the activity/VM runs [PlayerViewModel.castFromNowPlaying]. */
    const val ACTION_CAST_REQUESTED = "dev.voxhash.voxplayer.CAST_REQUESTED"

    /** Broadcast so the activity runs [PlayerViewModel.shareNowPlayingCard]. */
    const val ACTION_SHARE_REQUESTED = "dev.voxhash.voxplayer.SHARE_REQUESTED"
}
