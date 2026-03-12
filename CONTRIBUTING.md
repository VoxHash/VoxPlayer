# Contributing to VoxPlayer

Thanks for helping improve VoxPlayer!

## Code of Conduct

Please read and follow our [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Development Setup

```bash
# Clone
git clone https://github.com/voxhash/voxplayer.git
cd voxplayer

# Install deps
pip install -r requirements.txt

# Run tests
python test.py
```

## Branching & Commit Style

- Branches: `feature/…`, `fix/…`, `docs/…`, `chore/…`
- Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`

### Commit Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semicolons, etc.)
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `chore`: Build process or auxiliary tool changes

### Examples

```
feat(playlist): add shuffle mode
fix(audio): resolve volume amplification issue
docs: update README with new features
style: format code with black
refactor(ui): improve timeline component
test: add file association tests
chore: update build scripts
```

## Pull Requests

- Link related issues, add tests, update docs
- Follow the PR template
- Keep diffs focused
- Test on Windows, macOS, and Linux when possible
- Ensure code follows PEP 8 style guidelines

## Testing Guidelines

### Media Player Tests

When contributing, please test:
- [ ] Video playback (MP4, AVI, MKV, MOV, WMV, FLV, WebM, M4V)
- [ ] Audio playback (MP3, FLAC, WAV, OGG, M4A, AAC, WMA)
- [ ] File associations (double-click functionality)
- [ ] Command-line file opening
- [ ] Drag & drop functionality
- [ ] Playlist management
- [ ] Keyboard shortcuts
- [ ] Settings persistence
- [ ] Fullscreen mode
- [ ] Volume controls
- [ ] Timeline seeking

### Running Tests

```bash
# Run test suite
python test.py

# Test with sample files
python app.py "sample_video.mp4"
python app.py "sample_audio.mp3"

# Test file associations (Windows)
.\test_file_associations.bat
```

## Code Style

- Use **PEP 8** for Python code formatting
- Follow **PyQt6** best practices
- Use **type hints** where appropriate
- Write **clear, self-documenting code**
- Keep functions focused and small
- Use meaningful variable and function names

## Documentation

- Update documentation for new features
- Add docstrings for new functions
- Update README if needed
- Include examples in your code
- Update CHANGELOG.md for significant changes

## VoxPlayer Design Guidelines

When contributing to VoxPlayer's design or features:

### ✅ Do:
- Maintain ultra-compact design philosophy
- Keep interface clean and minimal
- Focus on functionality over decoration
- Ensure professional appearance
- Maintain cross-platform compatibility
- Keep performance as priority

### ❌ Don't:
- Add unnecessary UI elements
- Make interface cluttered
- Remove essential functionality
- Break file associations
- Ignore platform standards
- Compromise performance

## Release Process

- Semantic Versioning: `MAJOR.MINOR.PATCH`
- Update [CHANGELOG.md](CHANGELOG.md) before releases
- Tag releases with version numbers

## Getting Help

- **GitHub Issues**: Report bugs and request features
- **GitHub Discussions**: Ask questions and share ideas
- **Documentation**: See [README.md](README.md) and [docs/](docs/) for guides

---

**Made with ❤️ by VoxHash and the amazing community**

*VoxPlayer is ready to work with you!* 🎬✨
