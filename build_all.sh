#!/bin/bash
# VoxPlayer Cross-Platform Build Script
# Builds VoxPlayer for all supported platforms

set -e

echo "========================================"
echo "VoxPlayer Cross-Platform Builder"
echo "========================================"
echo ""

# Detect current platform
case "$OSTYPE" in
    darwin*)
        PLATFORM="macos"
        echo "Detected platform: macOS"
        ;;
    linux-gnu*)
        PLATFORM="linux"
        echo "Detected platform: Linux"
        ;;
    msys*|cygwin*|win32*)
        PLATFORM="windows"
        echo "Detected platform: Windows"
        ;;
    *)
        echo "WARNING: Unknown platform: $OSTYPE"
        PLATFORM="unknown"
        ;;
esac

echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to build for current platform
build_current_platform() {
    case $PLATFORM in
        "macos")
            echo "Building for macOS..."
            if [ -f "build_macos.sh" ]; then
                chmod +x build_macos.sh
                ./build_macos.sh
            else
                echo "ERROR: build_macos.sh not found"
                return 1
            fi
            ;;
        "linux")
            echo "Building for Linux..."
            if [ -f "build_debian.sh" ]; then
                chmod +x build_debian.sh
                ./build_debian.sh
            fi
            if [ -f "build_rpm.sh" ]; then
                chmod +x build_rpm.sh
                ./build_rpm.sh
            fi
            if [ -f "build_arch.sh" ]; then
                chmod +x build_arch.sh
                ./build_arch.sh
            fi
            ;;
        "windows")
            echo "Building for Windows..."
            if [ -f "build_simple.bat" ]; then
                ./build_simple.bat
            else
                echo "ERROR: build_simple.bat not found"
                return 1
            fi
            ;;
        *)
            echo "ERROR: Unsupported platform for building"
            return 1
            ;;
    esac
}

# Function to build source distribution
build_source() {
    echo "Building source distribution..."
    if [ -f "build_source.sh" ]; then
        chmod +x build_source.sh
        ./build_source.sh
    else
        echo "ERROR: build_source.sh not found"
        return 1
    fi
}

# Main build process
echo "Starting build process..."

# Always build source distribution
build_source

# Build for current platform
if [ "$PLATFORM" != "unknown" ]; then
    build_current_platform
else
    echo "WARNING: Cannot build for current platform"
fi

echo ""
echo "========================================"
echo "Build process completed!"
echo "========================================"
echo ""

# List created files
echo "Created files:"
ls -la *.tar.gz *.deb *.rpm *.dmg *.exe *.pkg.tar.zst 2>/dev/null || echo "No platform-specific packages found"

echo ""
echo "Installation instructions:"
echo ""

# Source distribution
if [ -f "VoxPlayer-1.0.0.tar.gz" ]; then
    echo "Source Distribution:"
    echo "  pip install VoxPlayer-1.0.0.tar.gz"
    echo ""
fi

# Platform-specific instructions
case $PLATFORM in
    "macos")
        if [ -f "VoxPlayer-1.0.0-macOS.dmg" ]; then
            echo "macOS:"
            echo "  Double-click VoxPlayer-1.0.0-macOS.dmg"
            echo "  Drag VoxPlayer.app to Applications folder"
            echo ""
        fi
        ;;
    "linux")
        if [ -f "voxplayer_1.0.0_amd64.deb" ]; then
            echo "Debian/Ubuntu:"
            echo "  sudo dpkg -i voxplayer_1.0.0_amd64.deb"
            echo "  sudo apt-get install -f  # Fix dependencies if needed"
            echo ""
        fi
        if [ -f "voxplayer-1.0.0-1.x86_64.rpm" ]; then
            echo "Fedora/CentOS/RHEL:"
            echo "  sudo dnf install voxplayer-1.0.0-1.x86_64.rpm"
            echo "  # or sudo yum install voxplayer-1.0.0-1.x86_64.rpm"
            echo ""
        fi
        if [ -f "voxplayer-1.0.0-1-x86_64.pkg.tar.zst" ]; then
            echo "Arch Linux:"
            echo "  sudo pacman -U voxplayer-1.0.0-1-x86_64.pkg.tar.zst"
            echo ""
        fi
        ;;
    "windows")
        if [ -f "dist/VoxPlayer.exe" ]; then
            echo "Windows:"
            echo "  Run dist/VoxPlayer.exe"
            echo "  Run register_file_associations.bat as Administrator"
            echo ""
        fi
        ;;
esac

echo "For more information, see README.md"
echo ""
echo "Build completed successfully! 🎬✨"
