#!/bin/bash
# VoxPlayer macOS Build Script
# Creates a .dmg installer for macOS

set -e

echo "========================================"
echo "VoxPlayer macOS Builder"
echo "========================================"
echo ""

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "ERROR: This script must be run on macOS"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.8+ and try again"
    exit 1
fi

# Check if PyInstaller is installed
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "Installing PyInstaller..."
    pip3 install pyinstaller
fi

# Check if create-dmg is installed
if ! command -v create-dmg &> /dev/null; then
    echo "Installing create-dmg..."
    if command -v brew &> /dev/null; then
        brew install create-dmg
    else
        echo "ERROR: Homebrew not found. Please install create-dmg manually:"
        echo "brew install create-dmg"
        exit 1
    fi
fi

echo "Installing dependencies..."
pip3 install -r requirements.txt

echo ""
echo "Building VoxPlayer executable..."
echo "This may take a few minutes..."
echo ""

# Clean previous builds
rm -rf dist build VoxPlayer.app

# Build the executable
python3 -m PyInstaller \
    --onefile \
    --windowed \
    --name VoxPlayer \
    --icon=icon.ico \
    --add-data "README.md:." \
    --add-data "LICENSE:." \
    --osx-bundle-identifier com.voxhash.voxplayer \
    --target-arch universal2 \
    app.py

# Check if executable was created
if [ ! -f "dist/VoxPlayer" ]; then
    echo "ERROR: VoxPlayer executable not found in dist folder"
    exit 1
fi

echo ""
echo "Creating macOS application bundle..."

# Create .app bundle structure
mkdir -p VoxPlayer.app/Contents/MacOS
mkdir -p VoxPlayer.app/Contents/Resources

# Copy executable
cp dist/VoxPlayer VoxPlayer.app/Contents/MacOS/

# Create Info.plist
cat > VoxPlayer.app/Contents/Info.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>VoxPlayer</string>
    <key>CFBundleIdentifier</key>
    <string>com.voxhash.voxplayer</string>
    <key>CFBundleName</key>
    <string>VoxPlayer</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>CFBundleDocumentTypes</key>
    <array>
        <dict>
            <key>CFBundleTypeExtensions</key>
            <array>
                <string>mp4</string>
                <string>avi</string>
                <string>mkv</string>
                <string>mov</string>
                <string>wmv</string>
                <string>flv</string>
                <string>webm</string>
                <string>m4v</string>
                <string>mp3</string>
                <string>flac</string>
                <string>wav</string>
                <string>ogg</string>
                <string>m4a</string>
                <string>aac</string>
                <string>wma</string>
            </array>
            <key>CFBundleTypeName</key>
            <string>Media File</string>
            <key>CFBundleTypeRole</key>
            <string>Viewer</string>
        </dict>
    </array>
</dict>
</plist>
EOF

# Copy icon
cp icon.ico VoxPlayer.app/Contents/Resources/icon.icns 2>/dev/null || echo "Warning: Could not copy icon"

# Copy documentation
cp README.md VoxPlayer.app/Contents/Resources/
cp LICENSE VoxPlayer.app/Contents/Resources/

echo ""
echo "Creating DMG installer..."

# Create DMG
create-dmg \
    --volname "VoxPlayer" \
    --volicon "icon.ico" \
    --window-pos 200 120 \
    --window-size 600 300 \
    --icon-size 100 \
    --icon "VoxPlayer.app" 175 120 \
    --hide-extension "VoxPlayer.app" \
    --app-drop-link 425 120 \
    "VoxPlayer-1.0.0-macOS.dmg" \
    "VoxPlayer.app"

if [ -f "VoxPlayer-1.0.0-macOS.dmg" ]; then
    echo ""
    echo "========================================"
    echo "macOS build completed successfully!"
    echo "========================================"
    echo ""
    echo "Files created:"
    echo "- VoxPlayer.app (Application bundle)"
    echo "- VoxPlayer-1.0.0-macOS.dmg (Installer)"
    echo ""
    echo "Installation:"
    echo "1. Double-click VoxPlayer-1.0.0-macOS.dmg"
    echo "2. Drag VoxPlayer.app to Applications folder"
    echo "3. VoxPlayer will be available in Applications"
    echo ""
else
    echo "ERROR: DMG creation failed"
    exit 1
fi
