#!/bin/bash
# VoxPlayer Fedora/CentOS/RHEL Build Script
# Creates a .rpm package for Fedora/CentOS/RHEL

set -e

echo "========================================"
echo "VoxPlayer Fedora/CentOS/RHEL Builder"
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

# Check if rpmbuild is available
if ! command -v rpmbuild &> /dev/null; then
    echo "ERROR: rpmbuild not found. Please install rpm-build:"
    echo "sudo dnf install rpm-build  # Fedora/CentOS 8+"
    echo "sudo yum install rpm-build  # CentOS 7"
    exit 1
fi

echo "Installing dependencies..."
pip3 install -r requirements.txt

echo ""
echo "Building VoxPlayer executable..."
echo "This may take a few minutes..."
echo ""

# Clean previous builds
rm -rf dist build ~/rpmbuild

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
echo "Creating RPM package structure..."

# Create RPM build directory
mkdir -p ~/rpmbuild/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}

# Create source tarball
tar -czf ~/rpmbuild/SOURCES/voxplayer-1.0.0.tar.gz \
    --transform 's,^,voxplayer-1.0.0/,' \
    app.py requirements.txt README.md LICENSE icon.ico

# Create spec file
cat > ~/rpmbuild/SPECS/voxplayer.spec << 'EOF'
Name:           voxplayer
Version:        1.0.0
Release:        1%{?dist}
Summary:        Ultra-compact media player

License:        MIT
URL:            https://github.com/voxhash/voxplayer
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-pip
BuildRequires:  python3-PyQt6
BuildRequires:  python3-PyQt6-qtmultimedia
BuildRequires:  python3-PyQt6-qtmultimediawidgets

Requires:       python3-PyQt6
Requires:       python3-PyQt6-qtmultimedia
Requires:       python3-PyQt6-qtmultimediawidgets

%description
VoxPlayer is a modern, ultra-compact media player for Linux with professional
file association support. Built with PyQt6 and designed for simplicity and
performance.

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

Supported formats:
- Video: MP4, AVI, MKV, MOV, WMV, FLV, WebM, M4V
- Audio: MP3, FLAC, WAV, OGG, M4A, AAC, WMA

%prep
%setup -q

%build
# Install dependencies
pip3 install -r requirements.txt

# Build executable
python3 -m PyInstaller \
    --onefile \
    --windowed \
    --name voxplayer \
    --add-data "README.md:." \
    --add-data "LICENSE:." \
    app.py

%install
rm -rf $RPM_BUILD_ROOT

# Install executable
install -d $RPM_BUILD_ROOT/usr/bin
install -m 755 dist/voxplayer $RPM_BUILD_ROOT/usr/bin/

# Install desktop file
install -d $RPM_BUILD_ROOT/usr/share/applications
cat > $RPM_BUILD_ROOT/usr/share/applications/voxplayer.desktop << 'DESKTOP_EOF'
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
DESKTOP_EOF

# Install icon
install -d $RPM_BUILD_ROOT/usr/share/pixmaps
install -m 644 icon.ico $RPM_BUILD_ROOT/usr/share/pixmaps/voxplayer.ico

# Install documentation
install -d $RPM_BUILD_ROOT/usr/share/doc/voxplayer
install -m 644 README.md $RPM_BUILD_ROOT/usr/share/doc/voxplayer/
install -m 644 LICENSE $RPM_BUILD_ROOT/usr/share/doc/voxplayer/

%files
/usr/bin/voxplayer
/usr/share/applications/voxplayer.desktop
/usr/share/pixmaps/voxplayer.ico
/usr/share/doc/voxplayer/README.md
/usr/share/doc/voxplayer/LICENSE

%changelog
* $(date '+%a %b %d %Y') VoxHash <voxhash@example.com> - 1.0.0-1
- Initial release
- Ultra-compact media player
- Support for 15+ media formats
- Advanced playlist management
- Professional file associations
EOF

# Build the RPM package
echo ""
echo "Building RPM package..."
rpmbuild -ba ~/rpmbuild/SPECS/voxplayer.spec

# Find the built package
RPM_FILE=$(find ~/rpmbuild/RPMS -name "voxplayer-*.rpm" | head -1)

if [ -f "$RPM_FILE" ]; then
    # Copy to current directory
    cp "$RPM_FILE" .
    RPM_NAME=$(basename "$RPM_FILE")
    
    echo ""
    echo "========================================"
    echo "RPM build completed successfully!"
    echo "========================================"
    echo ""
    echo "Files created:"
    echo "- $RPM_NAME (RPM package)"
    echo ""
    echo "Installation:"
    echo "sudo dnf install $RPM_NAME  # Fedora/CentOS 8+"
    echo "sudo yum install $RPM_NAME  # CentOS 7"
    echo ""
    echo "Uninstallation:"
    echo "sudo dnf remove voxplayer  # Fedora/CentOS 8+"
    echo "sudo yum remove voxplayer  # CentOS 7"
    echo ""
else
    echo "ERROR: RPM package creation failed"
    exit 1
fi
