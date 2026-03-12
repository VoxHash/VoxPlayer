#!/bin/bash
# VoxPlayer Debian/Ubuntu Build Script
# Creates a .deb package for Debian/Ubuntu

set -e

echo "========================================"
echo "VoxPlayer Debian/Ubuntu Builder"
echo "========================================"
echo ""

# Check if we're on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "ERROR: This script must be run on Linux"
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

# Check if dpkg-deb is available
if ! command -v dpkg-deb &> /dev/null; then
    echo "ERROR: dpkg-deb not found. Please install dpkg-dev:"
    echo "sudo apt-get install dpkg-dev"
    exit 1
fi

echo "Installing dependencies..."
pip3 install -r requirements.txt

echo ""
echo "Building VoxPlayer executable..."
echo "This may take a few minutes..."
echo ""

# Clean previous builds
rm -rf dist build voxplayer_1.0.0_amd64.deb

# Build the executable
python3 -m PyInstaller \
    --onefile \
    --windowed \
    --name voxplayer \
    --add-data "README.md:." \
    --add-data "LICENSE:." \
    app.py

# Check if executable was created
if [ ! -f "dist/voxplayer" ]; then
    echo "ERROR: VoxPlayer executable not found in dist folder"
    exit 1
fi

echo ""
echo "Creating Debian package structure..."

# Create package directory structure
PACKAGE_DIR="voxplayer_1.0.0_amd64"
rm -rf $PACKAGE_DIR
mkdir -p $PACKAGE_DIR/DEBIAN
mkdir -p $PACKAGE_DIR/usr/bin
mkdir -p $PACKAGE_DIR/usr/share/applications
mkdir -p $PACKAGE_DIR/usr/share/pixmaps
mkdir -p $PACKAGE_DIR/usr/share/doc/voxplayer
mkdir -p $PACKAGE_DIR/usr/share/voxplayer

# Copy executable
cp dist/voxplayer $PACKAGE_DIR/usr/bin/

# Make executable
chmod +x $PACKAGE_DIR/usr/bin/voxplayer

# Create desktop file
cat > $PACKAGE_DIR/usr/share/applications/voxplayer.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=VoxPlayer
Comment=Ultra-compact media player
Exec=voxplayer %F
Icon=voxplayer
Terminal=false
Categories=AudioVideo;Player;Video;
MimeType=video/mp4;video/avi;video/mkv;video/mov;video/wmv;video/flv;video/webm;video/m4v;audio/mp3;audio/flac;audio/wav;audio/ogg;audio/m4a;audio/aac;audio/wma;
StartupNotify=true
EOF

# Copy icon
cp icon.ico $PACKAGE_DIR/usr/share/pixmaps/voxplayer.ico 2>/dev/null || echo "Warning: Could not copy icon"

# Copy documentation
cp README.md $PACKAGE_DIR/usr/share/doc/voxplayer/
cp LICENSE $PACKAGE_DIR/usr/share/doc/voxplayer/

# Create changelog
cat > $PACKAGE_DIR/usr/share/doc/voxplayer/changelog << EOF
voxplayer (1.0.0) unstable; urgency=medium

  * Initial release
  * Ultra-compact media player
  * Support for 15+ media formats
  * Advanced playlist management
  * Professional file associations

 -- VoxHash <voxhash@example.com>  $(date -R)
EOF

# Create copyright
cat > $PACKAGE_DIR/usr/share/doc/voxplayer/copyright << EOF
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: VoxPlayer
Source: https://github.com/voxhash/voxplayer

Files: *
Copyright: 2024 VoxHash
License: MIT

License: MIT
 Permission is hereby granted, free of charge, to any person obtaining a copy
 of this software and associated documentation files (the "Software"), to deal
 in the Software without restriction, including without limitation the rights
 to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the Software is
 furnished to do so, subject to the following conditions:
 .
 The above copyright notice and this permission notice shall be included in all
 copies or substantial portions of the Software.
 .
 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 SOFTWARE.
EOF

# Create control file
cat > $PACKAGE_DIR/DEBIAN/control << EOF
Package: voxplayer
Version: 1.0.0
Section: sound
Priority: optional
Architecture: amd64
Depends: python3-pyqt6, python3-pyqt6.qtmultimedia, python3-pyqt6.qtmultimediawidgets
Maintainer: VoxHash <voxhash@example.com>
Description: Ultra-compact media player
 VoxPlayer is a modern, ultra-compact media player for Linux with professional
 file association support. Built with PyQt6 and designed for simplicity and
 performance.
 .
 Features:
  - Universal format support (15+ formats)
  - Ultra-compact design
  - True volume amplification up to 200%
  - Advanced playlist management
  - Professional file associations
  - Command-line support
  - Torrent streaming integration
  - Auto-update system
  - Audio device selection
  - Fullscreen mode with auto-hiding controls
  - Timeline preview
  - SRT subtitle support
  - Snapshot functionality
 .
 Supported formats:
  - Video: MP4, AVI, MKV, MOV, WMV, FLV, WebM, M4V
  - Audio: MP3, FLAC, WAV, OGG, M4A, AAC, WMA
EOF

# Create postinst script
cat > $PACKAGE_DIR/DEBIAN/postinst << EOF
#!/bin/bash
set -e

# Update desktop database
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications
fi

# Update mime database
if command -v update-mime-database >/dev/null 2>&1; then
    update-mime-database /usr/share/mime
fi

echo "VoxPlayer installed successfully!"
echo "You can now run 'voxplayer' from the command line or find it in your applications menu."
EOF

# Create prerm script
cat > $PACKAGE_DIR/DEBIAN/prerm << EOF
#!/bin/bash
set -e

# Update desktop database
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications
fi

# Update mime database
if command -v update-mime-database >/dev/null 2>&1; then
    update-mime-database /usr/share/mime
fi
EOF

# Make scripts executable
chmod +x $PACKAGE_DIR/DEBIAN/postinst
chmod +x $PACKAGE_DIR/DEBIAN/prerm

# Build the package
echo ""
echo "Building Debian package..."
dpkg-deb --build $PACKAGE_DIR

if [ -f "voxplayer_1.0.0_amd64.deb" ]; then
    echo ""
    echo "========================================"
    echo "Debian build completed successfully!"
    echo "========================================"
    echo ""
    echo "Files created:"
    echo "- voxplayer_1.0.0_amd64.deb (Debian package)"
    echo ""
    echo "Installation:"
    echo "sudo dpkg -i voxplayer_1.0.0_amd64.deb"
    echo "sudo apt-get install -f  # Fix dependencies if needed"
    echo ""
    echo "Uninstallation:"
    echo "sudo dpkg -r voxplayer"
    echo ""
else
    echo "ERROR: Debian package creation failed"
    exit 1
fi
