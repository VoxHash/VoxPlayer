package dev.voxhash.voxplayer.companion

import android.content.Context
import android.net.Uri
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import com.google.common.collect.ImmutableList

/**
 * Offline browse tree for Android Auto (MediaLibraryService).
 *
 * Root → Recent / Favorites / Playlists / Music. Audio-only for driver safety;
 * no cloud, no GMS Cast. Video stays on the phone/Quest UI.
 */
object CarMediaBrowser {
    const val ROOT_ID = "vox_root"
    const val FOLDER_RECENT = "folder_recent"
    const val FOLDER_FAVORITES = "folder_favorites"
    const val FOLDER_PLAYLISTS = "folder_playlists"
    const val FOLDER_MUSIC = "folder_music"
    private const val PLAYLIST_PREFIX = "playlist:"
    private const val TRACK_PREFIX = "track:"

    private const val PAGE_CAP = 200

    fun rootItem(): MediaItem =
        folderItem(
            id = ROOT_ID,
            title = "VoxPlayer",
            mediaType = MediaMetadata.MEDIA_TYPE_FOLDER_MIXED,
        )

    fun rootChildren(): ImmutableList<MediaItem> =
        ImmutableList.of(
            folderItem(FOLDER_RECENT, "Recent", MediaMetadata.MEDIA_TYPE_FOLDER_MIXED),
            folderItem(FOLDER_FAVORITES, "Favorites", MediaMetadata.MEDIA_TYPE_FOLDER_PLAYLISTS),
            folderItem(FOLDER_PLAYLISTS, "Playlists", MediaMetadata.MEDIA_TYPE_FOLDER_PLAYLISTS),
            folderItem(FOLDER_MUSIC, "Music", MediaMetadata.MEDIA_TYPE_FOLDER_MIXED),
        )

    fun children(
        context: Context,
        parentId: String,
        page: Int,
        pageSize: Int,
    ): ImmutableList<MediaItem> {
        val size = pageSize.coerceIn(1, PAGE_CAP)
        val offset = (page.coerceAtLeast(0) * size)
        return when {
            parentId == ROOT_ID -> rootChildren()
            parentId == FOLDER_RECENT -> pageList(recentTracks(context), offset, size)
            parentId == FOLDER_FAVORITES -> pageList(favoriteTracks(context), offset, size)
            parentId == FOLDER_PLAYLISTS -> pageList(playlistFolders(context), offset, size)
            parentId == FOLDER_MUSIC -> pageList(musicTracks(context), offset, size)
            parentId.startsWith(PLAYLIST_PREFIX) -> {
                val id = parentId.removePrefix(PLAYLIST_PREFIX)
                pageList(playlistTracks(context, id), offset, size)
            }
            else -> ImmutableList.of()
        }
    }

    fun resolvePlayable(context: Context, mediaId: String): MediaItem? {
        if (!mediaId.startsWith(TRACK_PREFIX)) return null
        val uriStr = mediaId.removePrefix(TRACK_PREFIX)
        if (uriStr.isBlank()) return null
        val uri = Uri.parse(uriStr)
        // Prefer rich MediaStore row when present
        LocalMediaStore.loadAudio(context, limit = 800).firstOrNull { it.uri.toString() == uriStr }
            ?.let { return playableFromLocal(it) }
        BookmarkStore(context).load().firstOrNull { it.uri == uriStr }?.let { b ->
            return playable(
                uri = uri,
                title = b.title,
                artist = "",
                album = "",
                isVideo = b.isVideo,
            )
        }
        PlayHistoryStore(context).load().firstOrNull { it.uri == uriStr }?.let { e ->
            return playable(
                uri = uri,
                title = e.title,
                artist = e.artist,
                album = e.album,
                isVideo = e.isVideo,
            )
        }
        LocalPlaylistStore(context).load().asSequence()
            .flatMap { it.tracks.asSequence() }
            .firstOrNull { it.uri == uriStr }
            ?.let { t ->
                return playable(
                    uri = uri,
                    title = t.title,
                    artist = t.artist,
                    album = t.album,
                    isVideo = t.isVideo,
                )
            }
        val title = uri.lastPathSegment ?: "Track"
        return playable(uri = uri, title = title, artist = "", album = "", isVideo = false)
    }

    fun resolveMediaItem(context: Context, item: MediaItem): MediaItem {
        val id = item.mediaId
        if (id.isNullOrBlank()) return item
        if (item.localConfiguration?.uri != null) return item
        return resolvePlayable(context, id) ?: item
    }

    private fun recentTracks(context: Context): List<MediaItem> =
        PlayHistoryStore(context).load().take(80).map { e ->
            playable(
                uri = Uri.parse(e.uri),
                title = e.title,
                artist = e.artist,
                album = e.album,
                isVideo = e.isVideo,
            )
        }.filter { !it.mediaMetadata.isVideoLike() }

    private fun favoriteTracks(context: Context): List<MediaItem> =
        BookmarkStore(context).load().take(100).map { b ->
            playable(
                uri = Uri.parse(b.uri),
                title = b.title,
                artist = "",
                album = "",
                isVideo = b.isVideo,
            )
        }.filter { !it.mediaMetadata.isVideoLike() }

    private fun playlistFolders(context: Context): List<MediaItem> =
        LocalPlaylistStore(context).load().map { pl ->
            folderItem(
                id = PLAYLIST_PREFIX + pl.id,
                title = pl.name.ifBlank { "Playlist" },
                mediaType = MediaMetadata.MEDIA_TYPE_FOLDER_PLAYLISTS,
                subtitle = "${pl.tracks.size} tracks",
            )
        }

    private fun playlistTracks(context: Context, playlistId: String): List<MediaItem> {
        val pl = LocalPlaylistStore(context).load().firstOrNull { it.id == playlistId } ?: return emptyList()
        return pl.tracks
            .filter { !it.isVideo }
            .map { t ->
                playable(
                    uri = Uri.parse(t.uri),
                    title = t.title,
                    artist = t.artist,
                    album = t.album,
                    isVideo = false,
                )
            }
    }

    private fun musicTracks(context: Context): List<MediaItem> =
        LocalMediaStore.loadAudio(context, limit = PAGE_CAP).map { playableFromLocal(it) }

    private fun playableFromLocal(item: LocalMediaItem): MediaItem =
        playable(
            uri = item.uri,
            title = item.title,
            artist = item.artist,
            album = item.album,
            isVideo = item.isVideo,
            durationMs = item.durationMs,
            artworkUri = if (!item.isVideo) item.artworkContentUri() else null,
        )

    private fun playable(
        uri: Uri,
        title: String,
        artist: String,
        album: String,
        isVideo: Boolean,
        durationMs: Long = 0L,
        artworkUri: Uri? = null,
    ): MediaItem {
        val displayArtist = artist.ifBlank { "VoxPlayer" }
        return MediaItem.Builder()
            .setMediaId(TRACK_PREFIX + uri.toString())
            .setUri(uri)
            .setMediaMetadata(
                MediaMetadata.Builder()
                    .setTitle(title)
                    .setDisplayTitle(title)
                    .setArtist(displayArtist)
                    .setSubtitle(
                        listOf(displayArtist, album).filter { it.isNotBlank() }.joinToString(" · "),
                    )
                    .apply {
                        if (album.isNotBlank()) setAlbumTitle(album)
                        if (durationMs > 0L) setDurationMs(durationMs)
                        if (artworkUri != null) setArtworkUri(artworkUri)
                        setMediaType(
                            if (isVideo) MediaMetadata.MEDIA_TYPE_VIDEO
                            else MediaMetadata.MEDIA_TYPE_MUSIC,
                        )
                    }
                    .setIsPlayable(true)
                    .setIsBrowsable(false)
                    .build(),
            )
            .build()
    }

    private fun folderItem(
        id: String,
        title: String,
        mediaType: Int,
        subtitle: String = "",
    ): MediaItem =
        MediaItem.Builder()
            .setMediaId(id)
            .setMediaMetadata(
                MediaMetadata.Builder()
                    .setTitle(title)
                    .setDisplayTitle(title)
                    .apply {
                        if (subtitle.isNotBlank()) setSubtitle(subtitle)
                    }
                    .setMediaType(mediaType)
                    .setIsBrowsable(true)
                    .setIsPlayable(false)
                    .build(),
            )
            .build()

    private fun pageList(items: List<MediaItem>, offset: Int, size: Int): ImmutableList<MediaItem> {
        if (offset >= items.size) return ImmutableList.of()
        val end = (offset + size).coerceAtMost(items.size)
        return ImmutableList.copyOf(items.subList(offset, end))
    }

    private fun MediaMetadata.isVideoLike(): Boolean =
        mediaType == MediaMetadata.MEDIA_TYPE_VIDEO ||
            mediaType == MediaMetadata.MEDIA_TYPE_MOVIE
}
