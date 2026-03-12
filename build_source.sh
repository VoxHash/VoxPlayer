#!/bin/bash
# VoxPlayer Source Distribution Build Script
# Creates a .tar.gz source distribution

set -e

echo "========================================"
echo "VoxPlayer Source Distribution Builder"
echo "========================================"
echo ""

# Clean previous builds
rm -rf VoxPlayer-1.0.0 VoxPlayer-1.0.0.tar.gz

echo "Creating source distribution..."

# Create source directory
mkdir -p VoxPlayer-1.0.0

# Copy source files
cp app.py VoxPlayer-1.0.0/
cp requirements.txt VoxPlayer-1.0.0/
cp README.md VoxPlayer-1.0.0/
cp LICENSE VoxPlayer-1.0.0/
cp CHANGELOG.md VoxPlayer-1.0.0/
cp CONTRIBUTING.md VoxPlayer-1.0.0/
cp ROADMAP.md VoxPlayer-1.0.0/
cp DEVELOPMENT_GOALS.md VoxPlayer-1.0.0/
cp icon.ico VoxPlayer-1.0.0/
cp voxplayer.spec VoxPlayer-1.0.0/
cp version_info.txt VoxPlayer-1.0.0/
cp VoxPlayer_Installer.iss VoxPlayer-1.0.0/
cp test.py VoxPlayer-1.0.0/
cp run.py VoxPlayer-1.0.0/
cp run.bat VoxPlayer-1.0.0/

# Copy build scripts
cp build_simple.bat VoxPlayer-1.0.0/
cp create_release.bat VoxPlayer-1.0.0/
cp build_installer.bat VoxPlayer-1.0.0/
cp build_macos.sh VoxPlayer-1.0.0/
cp build_debian.sh VoxPlayer-1.0.0/
cp build_rpm.sh VoxPlayer-1.0.0/
cp build_arch.sh VoxPlayer-1.0.0/
cp build_source.sh VoxPlayer-1.0.0/

# Copy file association scripts
cp register_file_associations.bat VoxPlayer-1.0.0/
cp unregister_file_associations.bat VoxPlayer-1.0.0/
cp test_file_associations.bat VoxPlayer-1.0.0/

# Create setup.py for source distribution
cat > VoxPlayer-1.0.0/setup.py << 'EOF'
#!/usr/bin/env python3
"""
VoxPlayer Setup Script
"""

from setuptools import setup, find_packages
import os

# Read README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="voxplayer",
    version="1.0.0",
    author="VoxHash",
    author_email="voxhash@example.com",
    description="Ultra-compact media player with professional file association support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/voxhash/voxplayer",
    project_urls={
        "Bug Reports": "https://github.com/voxhash/voxplayer/issues",
        "Source": "https://github.com/voxhash/voxplayer",
        "Documentation": "https://github.com/voxhash/voxplayer#readme",
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Video :: Display",
        "Topic :: Multimedia :: Sound/Audio :: Players",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
    ],
    keywords="media player video audio playlist pyqt6 desktop application",
    packages=find_packages(),
    py_modules=["app"],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "voxplayer=app:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt", "*.ico", "*.spec", "*.iss", "*.bat", "*.sh"],
    },
    zip_safe=False,
)
EOF

# Create MANIFEST.in
cat > VoxPlayer-1.0.0/MANIFEST.in << 'EOF'
include README.md
include LICENSE
include CHANGELOG.md
include CONTRIBUTING.md
include ROADMAP.md
include DEVELOPMENT_GOALS.md
include requirements.txt
include icon.ico
include voxplayer.spec
include version_info.txt
include VoxPlayer_Installer.iss
include test.py
include run.py
include run.bat
include build_simple.bat
include create_release.bat
include build_installer.bat
include build_macos.sh
include build_debian.sh
include build_rpm.sh
include build_arch.sh
include build_source.sh
include register_file_associations.bat
include unregister_file_associations.bat
include test_file_associations.bat
EOF

# Create installation instructions
cat > VoxPlayer-1.0.0/INSTALL.md << 'EOF'
# VoxPlayer Installation Instructions

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

## Installation

### Method 1: Using pip (Recommended)

```bash
# Install from source
pip install VoxPlayer-1.0.0.tar.gz

# Run VoxPlayer
voxplayer
```

### Method 2: Manual Installation

```bash
# Extract the source
tar -xzf VoxPlayer-1.0.0.tar.gz
cd VoxPlayer-1.0.0

# Install dependencies
pip install -r requirements.txt

# Run VoxPlayer
python app.py
```

## Platform-Specific Installation

### Windows
- Use the provided batch files for easy installation
- Run `build_simple.bat` to create an executable
- Run `register_file_associations.bat` as Administrator for file associations

### macOS
- Run `build_macos.sh` to create a .dmg installer
- Requires Xcode Command Line Tools and Homebrew

### Linux
- **Debian/Ubuntu**: Run `build_debian.sh` to create a .deb package
- **Fedora/CentOS/RHEL**: Run `build_rpm.sh` to create a .rpm package
- **Arch Linux**: Run `build_arch.sh` to create a pacman package

## Dependencies

- PyQt6 (GUI framework)
- PyQt6-QtMultimedia (Media playback)
- PyQt6-QtMultimediaWidgets (Media widgets)
- requests (HTTP requests)
- Other dependencies listed in requirements.txt

## Troubleshooting

If you encounter issues:

1. Ensure Python 3.8+ is installed
2. Install all dependencies: `pip install -r requirements.txt`
3. Check that PyQt6 is properly installed
4. Run from command line to see error messages

## Support

- GitHub Issues: https://github.com/voxhash/voxplayer/issues
- GitHub Discussions: https://github.com/voxhash/voxplayer/discussions
- Creator: VoxHash
EOF

# Create the tarball
tar -czf VoxPlayer-1.0.0.tar.gz VoxPlayer-1.0.0/

# Clean up
rm -rf VoxPlayer-1.0.0

if [ -f "VoxPlayer-1.0.0.tar.gz" ]; then
    echo ""
    echo "========================================"
    echo "Source distribution completed successfully!"
    echo "========================================"
    echo ""
    echo "Files created:"
    echo "- VoxPlayer-1.0.0.tar.gz (Source distribution)"
    echo ""
    echo "Installation:"
    echo "pip install VoxPlayer-1.0.0.tar.gz"
    echo ""
    echo "Or extract and install manually:"
    echo "tar -xzf VoxPlayer-1.0.0.tar.gz"
    echo "cd VoxPlayer-1.0.0"
    echo "pip install -r requirements.txt"
    echo "python app.py"
    echo ""
    echo "File size: $(du -h VoxPlayer-1.0.0.tar.gz | cut -f1)"
    echo ""
else
    echo "ERROR: Source distribution creation failed"
    exit 1
fi
