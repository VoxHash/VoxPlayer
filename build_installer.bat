@echo off
echo ========================================
echo VoxPlayer Windows Installer Builder
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

REM Check if PyInstaller is installed
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller
        pause
        exit /b 1
    )
)

REM Check if required packages are installed
echo Checking dependencies...
python -c "import PyQt6" >nul 2>&1
if errorlevel 1 (
    echo Installing PyQt6...
    pip install PyQt6
)

python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo Installing requests...
    pip install requests
)

python -c "import qbittorrent_api" >nul 2>&1
if errorlevel 1 (
    echo Installing qbittorrent-api...
    pip install qbittorrent-api
)

echo.
echo Building VoxPlayer executable...
echo This may take a few minutes...
echo.

REM Clean previous builds
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"

REM Build the executable
python -m PyInstaller --clean voxplayer.spec

if errorlevel 1 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo Executable location: dist\VoxPlayer.exe
echo.

REM Create a simple installer directory
echo Creating installer package...
if not exist "installer" mkdir "installer"
if not exist "installer\VoxPlayer" mkdir "installer\VoxPlayer"

REM Copy the executable
copy "dist\VoxPlayer.exe" "installer\VoxPlayer\"
if exist "dist\VoxPlayer.exe" (
    echo VoxPlayer.exe copied to installer package
) else (
    echo ERROR: VoxPlayer.exe not found in dist folder
    pause
    exit /b 1
)

REM Create a README for the installer
echo Creating installer README...
(
echo VoxPlayer - Advanced Media Player
echo =================================
echo.
echo Installation:
echo 1. Copy the VoxPlayer folder to your desired location
echo 2. Run VoxPlayer.exe to start the application
echo.
echo Features:
echo - Ultra-compact design for maximum efficiency
echo - Support for all major video and audio formats
echo - Advanced playlist management with search and filtering
echo - Torrent streaming support
echo - Drag and drop functionality
echo - True volume amplification up to 200%%
echo - Auto-update system
echo - Previous/Next media navigation
echo - Playlist import/export functionality
echo.
echo System Requirements:
echo - Windows 10 or later
echo - 4GB RAM minimum
echo - 100MB free disk space
echo.
echo For support and updates, visit:
echo https://github.com/voxhash/voxplayer
) > "installer\README.txt"

REM Create a simple installer script
(
echo @echo off
echo echo Installing VoxPlayer...
echo echo.
echo if not exist "C:\Program Files\VoxPlayer" mkdir "C:\Program Files\VoxPlayer"
echo xcopy /E /I /Y "VoxPlayer" "C:\Program Files\VoxPlayer\"
echo echo.
echo echo Creating desktop shortcut...
echo powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\VoxPlayer.lnk'^); $Shortcut.TargetPath = 'C:\Program Files\VoxPlayer\VoxPlayer.exe'; $Shortcut.Save()"
echo echo.
echo echo VoxPlayer installed successfully!
echo echo You can now run VoxPlayer from the desktop shortcut or Start menu.
echo pause
) > "installer\install.bat"

echo.
echo ========================================
echo Installer package created successfully!
echo ========================================
echo.
echo Installer location: installer\
echo - VoxPlayer\VoxPlayer.exe (Main executable)
echo - README.txt (Installation instructions)
echo - install.bat (Simple installer script)
echo.
echo To create a proper Windows installer, consider using:
echo - Inno Setup (free)
echo - NSIS (free)
echo - Advanced Installer (commercial)
echo.
echo For now, users can use the install.bat script or manually copy the VoxPlayer folder.
echo.
pause
