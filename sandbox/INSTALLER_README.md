# Franklin Installer System

This directory contains the installer infrastructure for Franklin Development Environment.

## Quick Start

### Build Installers (Unsigned)

```bash
# Build all installers
./build_native_installers.sh

# Output in dist/
# - Franklin-Installer-macOS.dmg
# - Franklin-Installer-Windows.exe
# - franklin_installer_gui.py
```

### Build Installers (Signed)

```bash
# Set signing credentials (see docs/pages/creating-trusted-installers.qmd)
export MACOS_CERTIFICATE_NAME="Developer ID Application: Your Name"
export WINDOWS_CERT_BASE64="..."

# Build signed installers
./build_native_installers.sh
```

## Architecture

### Core Components

```
master-installer.sh          # Main installation orchestrator (Unix)
Master-Installer.ps1         # Main installation orchestrator (Windows)
dependency_checker.py        # Cross-platform dependency state detection
```

### Platform-Specific Installers

```
macOS/
  macos_installer.applescript   # AppleScript GUI with radio buttons
  macos_installer_ui.swift      # Swift UI (future enhancement)

Windows/
  windows_installer_ui.ps1      # PowerShell Windows Forms GUI

Cross-platform/
  franklin_installer_gui.py     # Python Tkinter GUI (fallback)
```

### Individual Component Scripts

```
install-miniforge.sh / Install-Miniforge.ps1
install-pixi.sh / Install-Pixi.ps1
install-docker-desktop.sh / Install-Docker-Desktop.ps1
install-chrome.sh / Install-Chrome.ps1
```

## Features

### 1. Radio Button Interface
Each dependency shows:
- **None**: Skip installation
- **Install**: Install if not present
- **Reinstall**: Force reinstall
- **Uninstall**: Remove component

### 2. Dependency State Detection
- Checks if each component is installed
- Detects versions
- Identifies outdated or corrupted installations
- Grays out irrelevant options

### 3. User Role Selection
Users choose their role:
- **Student**: Installs `franklin` package (default)
- **Educator**: Installs `franklin-educator` package
- **Administrator**: Installs `franklin-admin` package

### 4. Smart Installation
- Skip already installed components
- Force reinstall specific components
- Handle failures gracefully
- Show real-time progress

## Building Installers

### Prerequisites

**macOS:**
```bash
# For Windows installer creation
brew install makensis

# For Windows code signing (optional)
brew install osslsigncode
```

**Windows:**
```powershell
# Install NSIS
winget install NSIS
```

### Build Process

1. **Run build script**: `./build_native_installers.sh`
2. **Script creates**:
   - macOS .app bundle → DMG
   - Windows NSIS installer → EXE
   - Python GUI script (cross-platform fallback)

### Output Structure

```
dist/
├── Franklin-Installer-macOS.dmg      # macOS installer
├── Franklin-Installer-Windows.exe    # Windows installer
├── franklin_installer_gui.py         # Python GUI
└── dependency_checker.py            # Dependency checker module
```

## Code Signing

### macOS Signing

Requirements:
- Apple Developer Account ($99/year)
- Developer ID Application certificate

Environment variables:
```bash
MACOS_CERTIFICATE_NAME    # Certificate name in Keychain
APPLE_ID                  # Apple ID email
APPLE_ID_PASSWORD         # App-specific password
TEAM_ID                   # Apple Developer Team ID
```

### Windows Signing

Requirements:
- Code Signing Certificate ($200-700/year)
- Standard or EV certificate

Environment variables:
```bash
WINDOWS_CERT_BASE64       # Base64-encoded PFX certificate
WINDOWS_CERT_PASSWORD     # Certificate password
```

## Testing

### Manual Testing

```bash
# Test unsigned installer (macOS)
open dist/Franklin-Installer-macOS.dmg
# Right-click the app → Open → Open

# Test Python GUI
python3 dist/franklin_installer_gui.py
```

### Automated Testing

```bash
# Run dependency checker tests
python3 -m pytest test_dependency_checker.py

# Verify installer creation
./build_native_installers.sh --test
```

## GitHub Actions Integration

The workflow automatically:
1. Builds installers on every push to main
2. Signs installers if certificates are configured
3. Uploads to GitHub Pages for documentation
4. Attaches to releases

See `.github/workflows/docs-and-installers.yml`

## User Experience

### First Run (Unsigned)

**macOS:**
1. User downloads DMG
2. Opens DMG, sees app
3. Double-clicks → Gatekeeper warning
4. Right-click → Open → Open to bypass

**Windows:**
1. User downloads EXE
2. Double-clicks → SmartScreen warning
3. Clicks "More info" → "Run anyway"

### First Run (Signed)

**macOS:**
1. User downloads DMG
2. Opens DMG, double-clicks app
3. Installer runs immediately

**Windows (EV Cert):**
1. User downloads EXE
2. Double-clicks
3. Installer runs immediately

**Windows (Standard Cert):**
1. Initial users see SmartScreen warning
2. After ~100 downloads, warning disappears

## Troubleshooting

### Build Failures

```bash
# Check prerequisites
which makensis  # Should show path
which osslsigncode  # Should show path (optional)

# Verbose build
./build_native_installers.sh --verbose

# Clean build
rm -rf build/ dist/
./build_native_installers.sh
```

### Signing Issues

```bash
# macOS: Check certificate
security find-identity -p codesigning -v

# macOS: Unlock keychain
security unlock-keychain login.keychain

# Windows: Verify certificate
echo $WINDOWS_CERT_BASE64 | base64 -d > test.pfx
openssl pkcs12 -info -in test.pfx -passin pass:$WINDOWS_CERT_PASSWORD
rm test.pfx
```

### Runtime Issues

```bash
# Check master installer directly
./master-installer.sh --help

# Test with specific components
./master-installer.sh --skip-docker --skip-chrome

# Force reinstall
./master-installer.sh --force-pixi --force-franklin
```

## Development

### Adding New Dependencies

1. Create installer scripts:
   ```bash
   install-yourtool.sh
   Install-YourTool.ps1
   ```

2. Update dependency_checker.py:
   ```python
   def check_yourtool(self):
       # Add detection logic
   ```

3. Update master-installer.sh:
   ```bash
   install_yourtool() {
       # Add installation logic
   }
   ```

4. Update GUI installers to include new option

### Modifying UI

- **macOS**: Edit `macos_installer.applescript`
- **Windows**: Edit `windows_installer_ui.ps1`
- **Python**: Edit `franklin_installer_gui.py`

## Support

For issues or questions:
1. Check [Creating Trusted Installers](../../docs/pages/creating-trusted-installers.qmd)
2. See [Windows Security](../../docs/pages/windows-security.qmd)
3. See [macOS Gatekeeper](../../docs/pages/macos-gatekeeper.qmd)
4. File issues at: https://github.com/franklin-project/franklin/issues