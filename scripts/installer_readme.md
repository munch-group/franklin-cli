# Native Installer Packages

This directory contains everything needed to create native installer packages for both Windows and macOS that wrap the development environment installer scripts.

## Overview

The native installers provide user-friendly graphical interfaces for installing the development environment, with options that map directly to the script command-line arguments:

- **Windows**: NSIS-based `.exe` installer with GUI checkboxes
- **macOS**: Native `.app` bundle with AppleScript dialogs

## Prerequisites

### For Building Windows Installer
- **NSIS (Nullsoft Scriptable Install System)**
  - Download from: https://nsis.sourceforge.io/
  - Install and add to your system PATH
  - Verify installation: `makensis /VERSION`

### For Building macOS Installer
- **macOS system** with osascript support (built-in)
- **Xcode Command Line Tools** (optional, for better compatibility)

### Required Installer Scripts
Both platforms require these installer scripts in the same directory:

**PowerShell Scripts (Windows):**
- `Install-Miniforge.ps1`
- `Install-Pixi.ps1`
- `Install-Docker-Desktop.ps1`
- `Install-Chrome.ps1`
- `Master-Installer.ps1`

**Bash Scripts (macOS/Linux):**
- `install-miniforge.sh`
- `install-pixi.sh`
- `install-docker-desktop.sh`
- `install-chrome.sh`
- `master-installer.sh`

## Building the Installers

### Quick Build (All Platforms)
```bash
# Make the build script executable
chmod +x build-installers.sh

# Build installers for all platforms
./build-installers.sh
```

### Platform-Specific Builds
```bash
# Build only Windows installer
./build-installers.sh --windows-only

# Build only macOS installer
./build-installers.sh --macos-only

# Clean build (remove previous builds)
./build-installers.sh --clean
```

### Manual Building

#### Windows NSIS Installer
1. Copy all PowerShell scripts to a directory
2. Copy the NSIS script (`installer.nsi`)
3. Run: `makensis installer.nsi`
4. Output: `DevEnvironmentInstaller.exe`

#### macOS App Bundle
1. Create the app bundle structure:
   ```bash
   mkdir -p "Development Environment Installer.app/Contents/MacOS"
   mkdir -p "Development Environment Installer.app/Contents/Resources"
   ```
2. Copy bash scripts to `Contents/Resources/`
3. Copy `Info.plist` to `Contents/`
4. Copy executable script to `Contents/MacOS/installer`
5. Make executable: `chmod +x "Contents/MacOS/installer"`

## Using the Installers

### Windows Installer (`DevEnvironmentInstaller.exe`)

1. **Run the installer** (requires administrator privileges)
2. **Welcome screen** - Click "Continue"
3. **Component selection** - Check/uncheck components to install:
   - ☑️ Miniforge (Python Distribution)
   - ☑️ Pixi (Package Manager)
   - ☑️ Docker Desktop
   - ☑️ Google Chrome
   - ☑️ Franklin (via Pixi)
4. **Installation options**:
   - ☐ Force reinstall if already installed
   - ☐ Continue on error (don't stop if one fails)
5. **Choose installation directory**
6. **Install** - Watch the PowerShell window for progress
7. **Finish** - Installation complete!

**Features:**
- Native Windows installer experience
- Automatic uninstaller creation
- Registry integration
- Administrator privilege handling
- Progress indication

### macOS App Bundle (`Development Environment Installer.app`)

1. **Launch the app** (double-click or right-click → Open)
2. **Welcome dialog** - Click "Continue"
3. **Component selection** - Select components from list (⌘+click for multiple):
   - Miniforge (Python Distribution)
   - Pixi (Package Manager)
   - Docker Desktop
   - Google Chrome
   - Franklin (via Pixi)
4. **Installation options** - Choose from:
   - Default (standard installation)
   - Force Only (reinstall if exists)
   - Continue Only (don't stop on errors)
   - Force + Continue (both options)
5. **Confirm installation** - Review selections and click "Install"
6. **Terminal window opens** - Watch progress in Terminal
7. **Completion** - Success dialog when finished

**Features:**
- Native macOS app experience
- AppleScript-based dialogs
- Terminal integration for progress
- Drag-and-drop installation from DMG

## Installer Options Mapping

The GUI options map directly to script command-line arguments:

| GUI Option | Windows PowerShell | macOS Bash |
|------------|-------------------|-------------|
| Skip Miniforge | `-SkipMiniforge` | `--skip-miniforge` |
| Skip Pixi | `-SkipPixi` | `--skip-pixi` |
| Skip Docker | `-SkipDocker` | `--skip-docker` |
| Skip Chrome | `-SkipChrome` | `--skip-chrome` |
| Skip Franklin | `-SkipFranklin` | `--skip-franklin` |
| Force reinstall | `-Force` | `--force` |
| Continue on error | `-ContinueOnError` | `--continue-on-error` |

## File Structure

```
project/
├── build-installers.sh          # Main build script
├── installer.nsi                # NSIS script for Windows
├── Info.plist                   # macOS app bundle info
├── Install-*.ps1                # PowerShell installer scripts
├── install-*.sh                 # Bash installer scripts
├── build/                       # Build directory (created)
│   ├── windows/                 # Windows build files
│   └── macos/                   # macOS build files
└── dist/                        # Final installer packages
    ├── DevEnvironmentInstaller.exe
    └── Development Environment Installer.app
```

## Troubleshooting

### Windows Issues

**"NSIS not found"**
- Install NSIS from https://nsis.sourceforge.io/
- Add NSIS to your system PATH
- Restart command prompt/PowerShell

**"Access denied" during installation**
- Run installer as Administrator
- Check Windows Defender/antivirus settings

**PowerShell execution policy errors**
- The installer uses `-ExecutionPolicy Bypass`
- Ensure PowerShell is available and not restricted

### macOS Issues

**"App can't be opened because it's from an unidentified developer"**
- Right-click the app and select "Open"
- Or go to System Preferences → Security & Privacy → General → "Open Anyway"

**Permission denied errors**
- The app may need Full Disk Access permissions
- System Preferences → Security & Privacy → Privacy → Full Disk Access

**Terminal doesn't open or commands fail**
- Ensure bash scripts are executable: `chmod +x *.sh`
- Check that all required scripts are in the app bundle

### General Issues

**Missing installer scripts**
- Ensure all required PowerShell and bash scripts are present
- Check that script names match exactly (case-sensitive on macOS)

**Installation failures**
- Check internet connectivity
- Verify administrator/sudo privileges
- Review Terminal/PowerShell output for specific errors

## Customization

### Modifying the GUI
- **Windows**: Edit the NSIS script (`installer.nsi`)
- **macOS**: Modify the AppleScript dialogs in the build script

### Adding New Components
1. Add new installer scripts (`.ps1` and `.sh`)
2. Update the GUI component lists
3. Add corresponding command-line argument mapping
4. Rebuild the installers

### Changing Branding
- Update `PRODUCT_NAME`, `PRODUCT_VERSION` in scripts
- Replace icons and images in NSIS script
- Modify app bundle Info.plist for macOS

## Building for Distribution

### Code Signing (Recommended for Production)

**Windows:**
- Sign the `.exe` with a code signing certificate
- Use SignTool: `signtool sign /f certificate.pfx DevEnvironmentInstaller.exe`

**macOS:**
- Sign the app bundle with Apple Developer certificate
- Use codesign: `codesign -s "Developer ID" "Development Environment Installer.app"`
- Notarize with Apple for Gatekeeper compatibility

### Creating Distribution Packages

**Windows:**
- The `.exe` is ready for distribution
- Consider creating a ZIP file with README

**macOS:**
- Create a DMG for easy distribution:
  ```bash
  hdiutil create -srcfolder "Development Environment Installer.app" \
    -volname "Dev Environment Installer" \
    DevEnvironmentInstaller.dmg
  ```

## Support

For issues with the installer packages:
1. Check the troubleshooting section above
2. Verify all prerequisite installer scripts are present
3. Review build script output for specific errors
4. Test on a clean system to identify environment issues

For issues with the underlying installation process, refer to the individual installer script documentation.