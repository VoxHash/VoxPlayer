#!/usr/bin/env python3
"""
VoxPlayer Launcher
Simple script to launch VoxPlayer with proper environment setup
"""

import sys
import os
import subprocess

def main():
    """Launch VoxPlayer"""
    print("🎬 Starting VoxPlayer...")
    
    # Set environment variables to suppress console output
    os.environ['QT_LOGGING_RULES'] = 'qt.multimedia.ffmpeg.debug=false'
    
    try:
        # Import and run the main application
        from app import main
        main()
    except ImportError as e:
        print(f"❌ Error: {e}")
        print("Please install dependencies with: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting VoxPlayer: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
