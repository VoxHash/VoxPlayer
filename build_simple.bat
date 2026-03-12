@echo off
echo ========================================
echo VoxPlayer Simple Builder
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

echo Installing PyInstaller...
pip install pyinstaller

echo.
echo Building VoxPlayer executable...
echo This may take a few minutes...
echo.

REM Clean previous builds
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"

REM Build the executable
python -m PyInstaller --onefile --windowed --name VoxPlayer --icon=icon.ico --add-data "README.md;." --add-data "LICENSE;." app.py

if errorlevel 1 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

REM Check if executable was created
if exist "dist\VoxPlayer.exe" (
    echo.
    echo ========================================
    echo Build completed successfully!
    echo ========================================
    echo.
    echo Executable location: dist\VoxPlayer.exe
    echo.
    echo You can now distribute VoxPlayer.exe to users.
    echo.
) else (
    echo ERROR: VoxPlayer.exe not found in dist folder
    pause
    exit /b 1
)

echo Creating distribution package...
if not exist "VoxPlayer_Distribution" mkdir "VoxPlayer_Distribution"
copy "dist\VoxPlayer.exe" "VoxPlayer_Distribution\"
copy "icon.ico" "VoxPlayer_Distribution\"
copy "register_file_associations.bat" "VoxPlayer_Distribution\"
copy "unregister_file_associations.bat" "VoxPlayer_Distribution\"
copy "README.md" "VoxPlayer_Distribution\"
copy "LICENSE" "VoxPlayer_Distribution\"
copy "requirements.txt" "VoxPlayer_Distribution\"

echo.
echo Distribution package created in: VoxPlayer_Distribution\
echo.
pause
