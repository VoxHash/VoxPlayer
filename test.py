#!/usr/bin/env python3
"""
VoxPlayer Test Script
Simple test to verify VoxPlayer functionality
"""

import sys
import os

def test_imports():
    """Test that all required modules can be imported"""
    print("🧪 Testing imports...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        print("✅ PyQt6.QtWidgets imported successfully")
    except ImportError as e:
        print(f"❌ PyQt6.QtWidgets import failed: {e}")
        return False
    
    try:
        from PyQt6.QtCore import Qt, QTimer
        print("✅ PyQt6.QtCore imported successfully")
    except ImportError as e:
        print(f"❌ PyQt6.QtCore import failed: {e}")
        return False
    
    try:
        from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
        print("✅ PyQt6.QtMultimedia imported successfully")
    except ImportError as e:
        print(f"❌ PyQt6.QtMultimedia import failed: {e}")
        return False
    
    try:
        from PyQt6.QtMultimediaWidgets import QVideoWidget
        print("✅ PyQt6.QtMultimediaWidgets imported successfully")
    except ImportError as e:
        print(f"❌ PyQt6.QtMultimediaWidgets import failed: {e}")
        return False
    
    try:
        import requests
        print("✅ requests imported successfully")
    except ImportError as e:
        print(f"❌ requests import failed: {e}")
        return False
    
    return True

def test_app_creation():
    """Test that the main application can be created"""
    print("🧪 Testing app creation...")
    
    try:
        from app import VoxPlayerMainWindow
        from PyQt6.QtWidgets import QApplication
        print("✅ VoxPlayerMainWindow class imported successfully")
        
        # Create QApplication
        app = QApplication(sys.argv)
        print("✅ QApplication created successfully")
        
        # Create main window
        window = VoxPlayerMainWindow()
        print("✅ VoxPlayerMainWindow created successfully")
        
        # Test basic functionality
        window.setWindowTitle("VoxPlayer Test")
        print("✅ Window title set successfully")
        
        # Clean up
        window.close()
        app.quit()
        print("✅ App cleanup completed successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ App creation failed: {e}")
        return False

def test_torrent_classes():
    """Test that torrent classes can be created"""
    print("🧪 Testing torrent classes...")
    
    try:
        from app import TorrentStreamer, UpdateChecker
        print("✅ TorrentStreamer class imported successfully")
        print("✅ UpdateChecker class imported successfully")
        
        # Test TorrentStreamer
        streamer = TorrentStreamer("magnet:?xt=urn:btih:test")
        print("✅ TorrentStreamer created successfully")
        
        # Test UpdateChecker
        checker = UpdateChecker("1.0.0")
        print("✅ UpdateChecker created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Torrent classes test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🎬 VoxPlayer Test Suite")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_app_creation,
        test_torrent_classes,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"🧪 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! VoxPlayer is ready to use.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
