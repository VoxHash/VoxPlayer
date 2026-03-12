@echo off
setlocal enabledelayedexpansion

echo ========================================
echo VoxPlayer Release Builder
echo ========================================
echo.

REM Set version
set VERSION=1.0.0
set BUILD_DIR=release_build
set INSTALLER_DIR=installer

REM Clean previous builds
echo Cleaning previous builds...
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
if exist "%INSTALLER_DIR%" rmdir /s /q "%INSTALLER_DIR%"
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"

REM Create directories
mkdir "%BUILD_DIR%"
mkdir "%INSTALLER_DIR%"

echo.
echo ========================================
echo Step 1: Installing Dependencies
echo ========================================

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

REM Install/upgrade required packages
echo Installing required packages...
pip install --upgrade pip
pip install --upgrade pyinstaller
pip install --upgrade PyQt6
pip install --upgrade requests
pip install --upgrade qbittorrent-api

echo.
echo ========================================
echo Step 2: Building Executable
echo ========================================

echo Building VoxPlayer executable...
python -m PyInstaller --clean voxplayer.spec

if errorlevel 1 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

REM Check if executable was created
if not exist "dist\VoxPlayer.exe" (
    echo ERROR: VoxPlayer.exe not found in dist folder
    pause
    exit /b 1
)

echo Executable built successfully!

echo.
echo ========================================
echo Step 3: Creating Release Package
echo ========================================

REM Copy executable to build directory
copy "dist\VoxPlayer.exe" "%BUILD_DIR%\"
copy "README.md" "%BUILD_DIR%\"
copy "LICENSE" "%BUILD_DIR%\"
copy "requirements.txt" "%BUILD_DIR%\"
copy "CHANGELOG.md" "%BUILD_DIR%\"

REM Create a simple installer
echo Creating simple installer package...
mkdir "%INSTALLER_DIR%\VoxPlayer"
copy "dist\VoxPlayer.exe" "%INSTALLER_DIR%\VoxPlayer\"
copy "README.md" "%INSTALLER_DIR%\VoxPlayer\"
copy "LICENSE" "%INSTALLER_DIR%\VoxPlayer\"

REM Create installer README
(
echo VoxPlayer v%VERSION% - Advanced Media Player
echo ============================================
echo.
echo INSTALLATION INSTRUCTIONS:
echo.
echo 1. Copy the VoxPlayer folder to your desired location
echo    (e.g., C:\Program Files\VoxPlayer\)
echo.
echo 2. Run VoxPlayer.exe to start the application
echo.
echo FEATURES:
echo - Ultra-compact design for maximum efficiency
echo - Support for all major video and audio formats
echo - Advanced playlist management with search and filtering
echo - Torrent streaming support with qBittorrent integration
echo - Drag and drop functionality for files and folders
echo - True volume amplification up to 200%%
echo - Auto-update system
echo - Previous/Next media navigation
echo - Playlist import/export functionality (M3U, PLS, XSPF)
echo - Clear playlist option with confirmation
echo - Smart playlist management (no auto-clearing)
echo - Audio device selection (Default/Manual)
echo - Fullscreen mode with auto-hiding controls
echo - Keyboard shortcuts for all major functions
echo.
echo SYSTEM REQUIREMENTS:
echo - Windows 10 or later (64-bit)
echo - 4GB RAM minimum (8GB recommended)
echo - 100MB free disk space
echo - qBittorrent (for torrent streaming)
echo.
echo KEYBOARD SHORTCUTS:
echo - Space: Play/Pause
echo - Ctrl+O: Open File
echo - Ctrl+Shift+O: Open Files
echo - Ctrl+Shift+F: Open Folder
echo - Ctrl+L: Toggle Playlist
echo - Ctrl+I: Import Playlist
echo - Ctrl+E: Export Playlist
echo - Ctrl+Shift+C: Clear Playlist
echo - Ctrl+M: Open Magnet Link
echo - Ctrl+T: Open Torrent File
echo - P: Previous Media
echo - N: Next Media
echo - F: Toggle Fullscreen
echo - Esc: Exit Fullscreen
echo - Ctrl+Q: Exit Application
echo.
echo SUPPORT:
echo - GitHub: https://github.com/voxhash/voxplayer
echo - Issues: https://github.com/voxhash/voxplayer/issues
echo - Email: jomasacadev@gmail.com
echo.
echo Copyright (c) 2025 VoxPlayer Team
echo Licensed under MIT License
) > "%INSTALLER_DIR%\README.txt"

REM Create simple installer script
(
echo @echo off
echo echo ========================================
echo echo VoxPlayer v%VERSION% Installer
echo echo ========================================
echo echo.
echo echo This will install VoxPlayer to C:\Program Files\VoxPlayer
echo echo.
echo pause
echo.
echo echo Creating installation directory...
echo if not exist "C:\Program Files\VoxPlayer" mkdir "C:\Program Files\VoxPlayer"
echo.
echo echo Copying files...
echo xcopy /E /I /Y "VoxPlayer" "C:\Program Files\VoxPlayer\"
echo.
echo echo Creating desktop shortcut...
echo powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%%USERPROFILE%%\Desktop\VoxPlayer.lnk'^); $Shortcut.TargetPath = 'C:\Program Files\VoxPlayer\VoxPlayer.exe'; $Shortcut.Description = 'VoxPlayer - Advanced Media Player'; $Shortcut.Save()"
echo.
echo echo Creating Start Menu shortcut...
echo powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%%APPDATA%%\Microsoft\Windows\Start Menu\Programs\VoxPlayer.lnk'^); $Shortcut.TargetPath = 'C:\Program Files\VoxPlayer\VoxPlayer.exe'; $Shortcut.Description = 'VoxPlayer - Advanced Media Player'; $Shortcut.Save()"
echo.
echo echo ========================================
echo echo Installation completed successfully!
echo echo ========================================
echo echo.
echo echo VoxPlayer has been installed to:
echo echo C:\Program Files\VoxPlayer\
echo echo.
echo echo You can now run VoxPlayer from:
echo echo - Desktop shortcut
echo echo - Start Menu
echo echo - C:\Program Files\VoxPlayer\VoxPlayer.exe
echo echo.
echo echo Thank you for using VoxPlayer!
echo echo.
echo pause
) > "%INSTALLER_DIR%\install.bat"

REM Create uninstaller script
(
echo @echo off
echo echo ========================================
echo echo VoxPlayer Uninstaller
echo echo ========================================
echo echo.
echo echo This will remove VoxPlayer from your system.
echo echo.
echo pause
echo.
echo echo Stopping VoxPlayer if running...
echo taskkill /f /im VoxPlayer.exe >nul 2>&1
echo.
echo echo Removing VoxPlayer files...
echo if exist "C:\Program Files\VoxPlayer" rmdir /s /q "C:\Program Files\VoxPlayer"
echo.
echo echo Removing shortcuts...
echo if exist "%%USERPROFILE%%\Desktop\VoxPlayer.lnk" del "%%USERPROFILE%%\Desktop\VoxPlayer.lnk"
echo if exist "%%APPDATA%%\Microsoft\Windows\Start Menu\Programs\VoxPlayer.lnk" del "%%APPDATA%%\Microsoft\Windows\Start Menu\Programs\VoxPlayer.lnk"
echo.
echo echo ========================================
echo echo VoxPlayer has been uninstalled.
echo echo ========================================
echo echo.
echo pause
) > "%INSTALLER_DIR%\uninstall.bat"

echo.
echo ========================================
echo Step 4: Creating ZIP Archive
echo ========================================

REM Create ZIP archive
echo Creating release archive...
powershell -Command "Compress-Archive -Path '%INSTALLER_DIR%\*' -DestinationPath 'VoxPlayer_v%VERSION%_Windows.zip' -Force"

if exist "VoxPlayer_v%VERSION%_Windows.zip" (
    echo Release archive created: VoxPlayer_v%VERSION%_Windows.zip
) else (
    echo WARNING: Failed to create ZIP archive
)

echo.
echo ========================================
echo Release Build Complete!
echo ========================================
echo.
echo Files created:
echo - %BUILD_DIR%\VoxPlayer.exe (Standalone executable)
echo - %INSTALLER_DIR%\VoxPlayer\ (Installer package)
echo - %INSTALLER_DIR%\install.bat (Simple installer)
echo - %INSTALLER_DIR%\uninstall.bat (Uninstaller)
echo - %INSTALLER_DIR%\README.txt (Installation instructions)
echo - VoxPlayer_v%VERSION%_Windows.zip (Release archive)
echo.
echo Next steps:
echo 1. Test the installer package
echo 2. Upload to GitHub releases
echo 3. Distribute to users
echo.
echo For a professional installer, use Inno Setup with VoxPlayer_Installer.iss
echo Download Inno Setup from: https://jrsoftware.org/isinfo.php
echo.
pause
