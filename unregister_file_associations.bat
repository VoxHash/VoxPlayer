@echo off
echo Unregistering VoxPlayer file associations...

echo.
echo Removing video file associations...

REM Remove video file associations
reg delete "HKEY_CLASSES_ROOT\.mp4" /f
reg delete "HKEY_CLASSES_ROOT\VoxPlayer.MP4" /f

reg delete "HKEY_CLASSES_ROOT\.avi" /f
reg delete "HKEY_CLASSES_ROOT\VoxPlayer.AVI" /f

reg delete "HKEY_CLASSES_ROOT\.mkv" /f
reg delete "HKEY_CLASSES_ROOT\VoxPlayer.MKV" /f

reg delete "HKEY_CLASSES_ROOT\.mov" /f
reg delete "HKEY_CLASSES_ROOT\VoxPlayer.MOV" /f

reg delete "HKEY_CLASSES_ROOT\.wmv" /f
reg delete "HKEY_CLASSES_ROOT\VoxPlayer.WMV" /f

reg delete "HKEY_CLASSES_ROOT\.flv" /f
reg delete "HKEY_CLASSES_ROOT\VoxPlayer.FLV" /f

reg delete "HKEY_CLASSES_ROOT\.webm" /f
reg delete "HKEY_CLASSES_ROOT\VoxPlayer.WEBM" /f

reg delete "HKEY_CLASSES_ROOT\.m4v" /f
reg delete "HKEY_CLASSES_ROOT\VoxPlayer.M4V" /f

echo.
echo Removing audio file associations...

REM Remove audio file associations
reg delete "HKEY_CLASSES_ROOT\.mp3" /f
reg delete "HKEY_CLASSES_ROOT\VoxPlayer.MP3" /f

reg delete "HKEY_CLASSES_ROOT\.flac" /f
reg delete "HKEY_CLASSES_ROOT\VoxPlayer.FLAC" /f

reg delete "HKEY_CLASSES_ROOT\.wav" /f
reg delete "HKEY_CLASSES_ROOT\VoxPlayer.WAV" /f

reg delete "HKEY_CLASSES_ROOT\.ogg" /f
reg delete "HKEY_CLASSES_ROOT\VoxPlayer.OGG" /f

reg delete "HKEY_CLASSES_ROOT\.m4a" /f
reg delete "HKEY_CLASSES_ROOT\VoxPlayer.M4A" /f

reg delete "HKEY_CLASSES_ROOT\.aac" /f
reg delete "HKEY_CLASSES_ROOT\VoxPlayer.AAC" /f

reg delete "HKEY_CLASSES_ROOT\.wma" /f
reg delete "HKEY_CLASSES_ROOT\VoxPlayer.WMA" /f

echo.
echo File associations unregistered successfully!
echo.
echo VoxPlayer is no longer the default player for media files.
echo.
pause
