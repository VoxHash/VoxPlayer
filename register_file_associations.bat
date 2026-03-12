@echo off
echo Registering VoxPlayer file associations...

REM Get the current directory (where VoxPlayer is located)
set "VOXPLAYER_PATH=%~dp0app.py"
set "VOXPLAYER_ICON=%~dp0icon.ico"

REM Convert to short path format
for %%i in ("%VOXPLAYER_PATH%") do set "VOXPLAYER_PATH=%%~si"
for %%i in ("%VOXPLAYER_ICON%") do set "VOXPLAYER_ICON=%%~si"

echo VoxPlayer path: %VOXPLAYER_PATH%
echo Icon path: %VOXPLAYER_ICON%

REM Register VoxPlayer as the default player for various media formats
echo.
echo Registering video file associations...

REM MP4 files
reg add "HKEY_CLASSES_ROOT\.mp4" /ve /d "VoxPlayer.MP4" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.MP4" /ve /d "MP4 Video File" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.MP4\DefaultIcon" /ve /d "%VOXPLAYER_ICON%" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.MP4\shell\open\command" /ve /d "python \"%VOXPLAYER_PATH%\" \"%%1\"" /f

REM AVI files
reg add "HKEY_CLASSES_ROOT\.avi" /ve /d "VoxPlayer.AVI" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.AVI" /ve /d "AVI Video File" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.AVI\DefaultIcon" /ve /d "%VOXPLAYER_ICON%" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.AVI\shell\open\command" /ve /d "python \"%VOXPLAYER_PATH%\" \"%%1\"" /f

REM MKV files
reg add "HKEY_CLASSES_ROOT\.mkv" /ve /d "VoxPlayer.MKV" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.MKV" /ve /d "MKV Video File" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.MKV\DefaultIcon" /ve /d "%VOXPLAYER_ICON%" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.MKV\shell\open\command" /ve /d "python \"%VOXPLAYER_PATH%\" \"%%1\"" /f

REM MOV files
reg add "HKEY_CLASSES_ROOT\.mov" /ve /d "VoxPlayer.MOV" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.MOV" /ve /d "MOV Video File" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.MOV\DefaultIcon" /ve /d "%VOXPLAYER_ICON%" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.MOV\shell\open\command" /ve /d "python \"%VOXPLAYER_PATH%\" \"%%1\"" /f

REM WMV files
reg add "HKEY_CLASSES_ROOT\.wmv" /ve /d "VoxPlayer.WMV" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.WMV" /ve /d "WMV Video File" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.WMV\DefaultIcon" /ve /d "%VOXPLAYER_ICON%" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.WMV\shell\open\command" /ve /d "python \"%VOXPLAYER_PATH%\" \"%%1\"" /f

REM FLV files
reg add "HKEY_CLASSES_ROOT\.flv" /ve /d "VoxPlayer.FLV" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.FLV" /ve /d "FLV Video File" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.FLV\DefaultIcon" /ve /d "%VOXPLAYER_ICON%" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.FLV\shell\open\command" /ve /d "python \"%VOXPLAYER_PATH%\" \"%%1\"" /f

REM WebM files
reg add "HKEY_CLASSES_ROOT\.webm" /ve /d "VoxPlayer.WEBM" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.WEBM" /ve /d "WebM Video File" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.WEBM\DefaultIcon" /ve /d "%VOXPLAYER_ICON%" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.WEBM\shell\open\command" /ve /d "python \"%VOXPLAYER_PATH%\" \"%%1\"" /f

REM M4V files
reg add "HKEY_CLASSES_ROOT\.m4v" /ve /d "VoxPlayer.M4V" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.M4V" /ve /d "M4V Video File" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.M4V\DefaultIcon" /ve /d "%VOXPLAYER_ICON%" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.M4V\shell\open\command" /ve /d "python \"%VOXPLAYER_PATH%\" \"%%1\"" /f

echo.
echo Registering audio file associations...

REM MP3 files
reg add "HKEY_CLASSES_ROOT\.mp3" /ve /d "VoxPlayer.MP3" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.MP3" /ve /d "MP3 Audio File" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.MP3\DefaultIcon" /ve /d "%VOXPLAYER_ICON%" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.MP3\shell\open\command" /ve /d "python \"%VOXPLAYER_PATH%\" \"%%1\"" /f

REM FLAC files
reg add "HKEY_CLASSES_ROOT\.flac" /ve /d "VoxPlayer.FLAC" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.FLAC" /ve /d "FLAC Audio File" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.FLAC\DefaultIcon" /ve /d "%VOXPLAYER_ICON%" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.FLAC\shell\open\command" /ve /d "python \"%VOXPLAYER_PATH%\" \"%%1\"" /f

REM WAV files
reg add "HKEY_CLASSES_ROOT\.wav" /ve /d "VoxPlayer.WAV" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.WAV" /ve /d "WAV Audio File" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.WAV\DefaultIcon" /ve /d "%VOXPLAYER_ICON%" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.WAV\shell\open\command" /ve /d "python \"%VOXPLAYER_PATH%\" \"%%1\"" /f

REM OGG files
reg add "HKEY_CLASSES_ROOT\.ogg" /ve /d "VoxPlayer.OGG" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.OGG" /ve /d "OGG Audio File" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.OGG\DefaultIcon" /ve /d "%VOXPLAYER_ICON%" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.OGG\shell\open\command" /ve /d "python \"%VOXPLAYER_PATH%\" \"%%1\"" /f

REM M4A files
reg add "HKEY_CLASSES_ROOT\.m4a" /ve /d "VoxPlayer.M4A" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.M4A" /ve /d "M4A Audio File" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.M4A\DefaultIcon" /ve /d "%VOXPLAYER_ICON%" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.M4A\shell\open\command" /ve /d "python \"%VOXPLAYER_PATH%\" \"%%1\"" /f

REM AAC files
reg add "HKEY_CLASSES_ROOT\.aac" /ve /d "VoxPlayer.AAC" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.AAC" /ve /d "AAC Audio File" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.AAC\DefaultIcon" /ve /d "%VOXPLAYER_ICON%" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.AAC\shell\open\command" /ve /d "python \"%VOXPLAYER_PATH%\" \"%%1\"" /f

REM WMA files
reg add "HKEY_CLASSES_ROOT\.wma" /ve /d "VoxPlayer.WMA" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.WMA" /ve /d "WMA Audio File" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.WMA\DefaultIcon" /ve /d "%VOXPLAYER_ICON%" /f
reg add "HKEY_CLASSES_ROOT\VoxPlayer.WMA\shell\open\command" /ve /d "python \"%VOXPLAYER_PATH%\" \"%%1\"" /f

echo.
echo File associations registered successfully!
echo.
echo VoxPlayer is now the default player for:
echo - Video files: MP4, AVI, MKV, MOV, WMV, FLV, WebM, M4V
echo - Audio files: MP3, FLAC, WAV, OGG, M4A, AAC, WMA
echo.
echo You can now double-click any supported media file to open it with VoxPlayer!
echo.
pause
