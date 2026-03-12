@echo off
echo Testing VoxPlayer file association functionality...
echo.

REM Test with a sample video file (if it exists)
if exist "test_video.mp4" (
    echo Testing with test_video.mp4...
    python app.py "test_video.mp4"
) else (
    echo No test video found. Creating a test...
    echo.
    echo To test file associations:
    echo 1. Run: register_file_associations.bat
    echo 2. Double-click any supported media file
    echo 3. VoxPlayer should open and play the file
    echo.
    echo Supported formats:
    echo - Video: MP4, AVI, MKV, MOV, WMV, FLV, WebM, M4V
    echo - Audio: MP3, FLAC, WAV, OGG, M4A, AAC, WMA
    echo.
    echo To remove associations later, run: unregister_file_associations.bat
)

echo.
pause
