#!/bin/bash
# VoxPlayer Arch Linux Build Script
# Creates a pacman package for Arch Linux

set -e

echo "========================================"
echo "VoxPlayer Arch Linux Builder"
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

# Check if makepkg is available
if ! command -v makepkg &> /dev/null; then
    echo "ERROR: makepkg not found. Please install base-devel:"
    echo "sudo pacman -S base-devel"
    exit 1
fi

echo "Installing dependencies..."
pip3 install -r requirements.txt

echo ""
echo "Building VoxPlayer executable..."
echo "This may take a few minutes..."
echo ""

# Clean previous builds
rm -rf dist build pkg src

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
echo "Creating Arch Linux package structure..."

# Create PKGBUILD
cat > PKGBUILD << 'EOF'
# Maintainer: VoxHash <voxhash@example.com>
pkgname=voxplayer
pkgver=1.0.0
pkgrel=1
pkgdesc="Ultra-compact media player with professional file association support"
arch=('x86_64')
url="https://github.com/voxhash/voxplayer"
license=('MIT')
depends=('python-pyqt6' 'python-pyqt6-qtmultimedia' 'python-pyqt6-qtmultimediawidgets')
makedepends=('python-pip' 'python-pyinstaller')
source=("$pkgname-$pkgver.tar.gz")
sha256sums=('SKIP')

build() {
    cd "$pkgname-$pkgver"
    
    # Install dependencies
    pip install -r requirements.txt
    
    # Build executable
    python -m PyInstaller \
        --onefile \
        --windowed \
        --name voxplayer \
        --add-data "README.md:." \
        --add-data "LICENSE:." \
        app.py
}

package() {
    cd "$pkgname-$pkgver"
    
    # Install executable
    install -Dm755 dist/voxplayer "$pkgdir/usr/bin/voxplayer"
    
    # Install desktop file
    install -Dm644 voxplayer.desktop "$pkgdir/usr/share/applications/voxplayer.desktop"
    
    # Install icon
    install -Dm644 icon.ico "$pkgdir/usr/share/pixmaps/voxplayer.ico"
    
    # Install documentation
    install -Dm644 README.md "$pkgdir/usr/share/doc/voxplayer/README.md"
    install -Dm644 LICENSE "$pkgdir/usr/share/doc/voxplayer/LICENSE"
}

# vim:set ts=2 sw=2 et:
EOF

# Create desktop file
cat > voxplayer.desktop << 'EOF'
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

# Create source tarball
mkdir -p voxplayer-1.0.0
cp app.py requirements.txt README.md LICENSE icon.ico voxplayer.desktop voxplayer-1.0.0/
tar -czf voxplayer-1.0.0.tar.gz voxplayer-1.0.0/

# Update PKGBUILD with correct checksum
SHA256SUM=$(sha256sum voxplayer-1.0.0.tar.gz | cut -d' ' -f1)
sed -i "s/SKIP/$SHA256SUM/" PKGBUILD

# Build the package
echo ""
echo "Building Arch Linux package..."
makepkg -s

# Find the built package
PKG_FILE=$(find . -name "voxplayer-*.pkg.tar.zst" | head -1)

if [ -f "$PKG_FILE" ]; then
    echo ""
    echo "========================================"
    echo "Arch Linux build completed successfully!"
    echo "========================================"
    echo ""
    echo "Files created:"
    echo "- $PKG_FILE (Arch Linux package)"
    echo ""
    echo "Installation:"
    echo "sudo pacman -U $PKG_FILE"
    echo ""
    echo "Uninstallation:"
    echo "sudo pacman -R voxplayer"
    echo ""
    echo "To install from AUR (if published):"
    echo "yay -S voxplayer  # or your preferred AUR helper"
    echo ""
else
    echo "ERROR: Arch Linux package creation failed"
    exit 1
fi
