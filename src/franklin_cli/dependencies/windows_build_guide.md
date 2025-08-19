# Windows Installer Build Guide

This guide explains how to build a native Windows installer for the Development Environment tools using the PowerShell build script.

## Quick Start

### Prerequisites

1. **NSIS (Nullsoft Scriptable Install System)**
   - Download from: https://nsis.sourceforge.io/
   - Install and ensure `makensis.exe` is in your PATH
   - Minimum version: 3.0.0

2. **PowerShell 5.1 or later** (included with Windows 10+)

3. **Required PowerShell Scripts** (must be in the same directory):
   - `Install-Miniforge.ps1`
   - `Install-Pixi.ps1`
   - `Install-Docker-Desktop.ps1`
   - `Install-Chrome.ps1`
   - `Master-Installer.ps1`

### Build Methods

#### Method 1: Batch File (Easiest)
```cmd
# Simple build
build-installer.bat

# Verbose build with cleanup
build-installer.bat --verbose --clean
```

#### Method 2: PowerShell Script (Advanced)
```powershell
# Basic build
 powershell -ExecutionPolicy Bypass -File .\Build-WindowsInstaller.ps1

# Custom build
.\Build-WindowsInstaller.ps1 -OutputPath "C:\Release" -ProductVersion "2.0.0" -Verbose

# Clean build
.\Build-WindowsInstaller.ps1 -Clean -Verbose
```

## Build Process

The build script performs these steps:

1. **Prerequisites Check** - Verifies NSIS, PowerShell, and required scripts
2. **Environment Setup** - Creates build and output directories
3. **Script Copying** - Copies PowerShell scripts to build directory
4. **NSIS Generation** - Creates the installer script with GUI components
5. **Compilation** - Runs `makensis.exe` to build the .exe installer
6. **Verification** - Tests the output installer file
7. **Cleanup** - Removes temporary build files (unless verbose mode)

## Output

### Success
- **Installer file**: `dist/DevEnvironmentInstaller.exe`
- **Size**: Typically 2-5 MB
- **Features**: GUI component selection, uninstaller, registry integration

### Directory Structure
```
project/
├── Build-WindowsInstaller.ps1    # Main build script
├── build-installer.bat           # Batch wrapper
├── Install-*.ps1                 # PowerShell installer scripts
├── build/                        # Temporary build files
│   └── windows/
│       ├── installer.nsi         # Generated NSIS script
│       └── *.ps1                 # Copied installer scripts
└── dist/                         # Final output
    └── DevEnvironmentInstaller.exe
```

## Build Options

### PowerShell Script Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `-OutputPath` | Output directory for installer | `.\dist` |
| `-BuildPath` | Temporary build directory | `.\build\windows` |
| `-ScriptPath` | Directory with PowerShell scripts | `.` |
| `-InstallerName` | Output installer filename | `DevEnvironmentInstaller.exe` |
| `-ProductVersion` | Installer version | `1.0.0` |
| `-Clean` | Clean build directory first | False |
| `-SkipNsisCheck` | Skip NSIS installation check | False |
| `-Verbose` | Enable verbose output | False |

### Examples

```powershell
# Custom output location and version
.\Build-WindowsInstaller.ps1 -OutputPath "C:\Release" -ProductVersion "1.2.0"

# Build with different script location
.\Build-WindowsInstaller.ps1 -ScriptPath "C:\Scripts" -Verbose

# Force clean build
.\Build-WindowsInstaller.ps1 -Clean -Verbose

# Quick build without NSIS check (advanced users)
.\Build-WindowsInstaller.ps1 -SkipNsisCheck
```

## Installer Features

### GUI Components
The built installer includes:
- **Welcome page** with product information
- **Component selection** with checkboxes for:
  - Miniforge (Python Distribution)
  - Pixi (Package Manager)  
  - Docker Desktop
  - Google Chrome
  - Franklin (via Pixi)
- **Installation options**:
  - Force reinstall if already installed
  - Continue on error (don't stop if one fails)
- **Directory selection** for installer files
- **Progress indication** during installation
- **Completion page** with next steps

### Technical Features
- **Administrator privileges** automatically requested
- **Registry integration** for proper Windows integration
- **Automatic uninstaller** creation and registration
- **Error handling** with user-friendly messages
- **PowerShell execution** with proper security policies
- **Component detection** before installation

## Troubleshooting

### Common Issues

**"NSIS not found in PATH"**
```cmd
# Solution: Install NSIS and add to PATH
# 1. Download NSIS from https://nsis.sourceforge.io/
# 2. Install with default options
# 3. Add C:\Program Files (x86)\NSIS to your PATH
# 4. Restart command prompt and try again
```

**"Missing required PowerShell scripts"**
```cmd
# Solution: Ensure all scripts are present
dir *.ps1
# Should show: Install-Miniforge.ps1, Install-Pixi.ps1, etc.
```

**"Access denied" or permission errors**
```cmd
# Solution: Run as Administrator
# Right-click Command Prompt and select "Run as administrator"
```

**"PowerShell execution policy" errors**
```powershell
# Solution: The build script uses -ExecutionPolicy Bypass
# If still having issues, try:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Debug Mode

Enable verbose output for detailed troubleshooting:

```powershell
.\Build-WindowsInstaller.ps1 -Verbose
```

This will:
- Show detailed NSIS compilation output
- Display generated NSIS script content
- Keep build artifacts for inspection
- Provide step-by-step progress information

### Manual NSIS Compilation

If the build script fails, you can manually compile:

```cmd
cd build\windows
makensis.exe /V3 installer.nsi
```

## Advanced Configuration

### Customizing the Installer

Edit the PowerShell script to modify:

**Product Information** (lines 25-30):
```powershell
ProductName = "Your Custom Installer"
ProductPublisher = "Your Company"
ProductWebsite = "https://your-website.com"
```

**NSIS Script Template** (New-NsisScript function):
- Modify GUI layout and text
- Add custom branding/icons
- Change default component selections
- Customize installation behavior

### Code Signing

For production distribution, sign the installer:

```cmd
# Using SignTool (requires code signing certificate)
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com DevEnvironmentInstaller.exe

# Using PowerShell (alternative method)
Set-AuthenticodeSignature -FilePath "DevEnvironmentInstaller.exe" -Certificate $cert
```

### Creating Distribution Package

```powershell
# Create release package
$version = "1.0.0"
$packageName = "DevEnvironmentInstaller-v$version"

# Create package directory
New-Item -ItemType Directory -Path $packageName

# Copy installer and documentation
Copy-Item "dist\DevEnvironmentInstaller.exe" $packageName
Copy-Item "README.md" $packageName
Copy-Item "LICENSE" $packageName

# Create ZIP package
Compress-Archive -Path $packageName -DestinationPath "$packageName.zip"
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build Windows Installer

on:
  push:
    tags: ['v*']

jobs:
  build:
    runs-on: windows-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Install NSIS
      run: |
        choco install nsis -y
        
    - name: Build Installer
      run: |
        .\Build-WindowsInstaller.ps1 -ProductVersion "${{ github.ref_name }}"
        
    - name: Upload Artifact
      uses: actions/upload-artifact@v3
      with:
        name: windows-installer
        path: dist/DevEnvironmentInstaller.exe
```

### Azure DevOps Example

```yaml
trigger:
  tags:
    include: ['v*']

pool:
  vmImage: 'windows-latest'

steps:
- task: PowerShell@2
  displayName: 'Install NSIS'
  inputs:
    targetType: 'inline'
    script: 'choco install nsis -y'

- task: PowerShell@2
  displayName: 'Build Installer'
  inputs:
    filePath: 'Build-WindowsInstaller.ps1'
    arguments: '-ProductVersion "$(Build.SourceBranchName)"'

- task: PublishBuildArtifacts@1
  inputs:
    pathToPublish: 'dist'
    artifactName: 'windows-installer'
```

## Support

For issues with the build process:

1. **Check Prerequisites** - Ensure NSIS and all scripts are present
2. **Run with Verbose** - Use `-Verbose` flag for detailed output  
3. **Review Logs** - Check build output for specific error messages
4. **Test Manually** - Try manual NSIS compilation if automated build fails
5. **Environment** - Verify PowerShell version and execution policies

The build script includes comprehensive error checking and will guide you through resolving most common issues.