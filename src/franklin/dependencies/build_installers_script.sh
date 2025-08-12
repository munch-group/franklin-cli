#!/bin/bash

# Cross-Platform Installer Build Script
# Builds native installer packages for both Windows (NSIS) and macOS (.app bundle)

set -euo pipefail

# Configuration
PRODUCT_NAME="Development Environment Installer"
PRODUCT_VERSION="1.0.0"
BUILD_DIR="$(pwd)/build"
DIST_DIR="$(pwd)/dist"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_header() {
    echo
    echo -e "${CYAN}============================================================${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}============================================================${NC}"
}

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if required script files exist
    local required_files=(
        "Install-Miniforge.ps1"
        "Install-Pixi.ps1"
        "Install-Docker-Desktop.ps1"
        "Install-Chrome.ps1"
        "Master-Installer.ps1"
        "install-miniforge.sh"
        "install-pixi.sh"
        "install-docker-desktop.sh"
        "install-chrome.sh"
        "master-installer.sh"
    )
    
    local missing_files=()
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -gt 0 ]; then
        log_error "Missing required installer scripts:"
        for file in "${missing_files[@]}"; do
            echo "  - $file"
        done
        log_error "Please ensure all installer scripts are in the current directory."
        exit 1
    fi
    
    log_success "All required installer scripts found"
}

# Function to create build directories
setup_build_environment() {
    log_info "Setting up build environment..."
    
    # Create build and dist directories
    mkdir -p "$BUILD_DIR"
    mkdir -p "$DIST_DIR"
    
    # Create subdirectories for each platform
    mkdir -p "$BUILD_DIR/windows"
    mkdir -p "$BUILD_DIR/macos"
    
    log_success "Build environment ready"
}

# Function to build Windows NSIS installer
build_windows_installer() {
    log_header "Building Windows NSIS Installer"
    
    local windows_build_dir="$BUILD_DIR/windows"
    
    # Check if NSIS is available
    if ! command -v makensis >/dev/null 2>&1; then
        log_warning "NSIS (makensis) not found. Skipping Windows installer build."
        log_info "To build Windows installer:"
        log_info "1. Install NSIS from https://nsis.sourceforge.io/"
        log_info "2. Add NSIS to your PATH"
        log_info "3. Run this script again"
        return 1
    fi
    
    # Copy PowerShell scripts to build directory
    log_info "Copying PowerShell scripts..."
    cp Install-Miniforge.ps1 "$windows_build_dir/"
    cp Install-Pixi.ps1 "$windows_build_dir/"
    cp Install-Docker-Desktop.ps1 "$windows_build_dir/"
    cp Install-Chrome.ps1 "$windows_build_dir/"
    cp Master-Installer.ps1 "$windows_build_dir/"
    
    # Create NSIS script
    log_info "Creating NSIS installer script..."
    cat > "$windows_build_dir/installer.nsi" << 'NSIS_EOF'
# Development Environment Installer
# NSIS Script for Windows Installer Package

!define PRODUCT_NAME "Development Environment Installer"
!define PRODUCT_VERSION "1.0.0"
!define PRODUCT_PUBLISHER "Development Team"
!define PRODUCT_WEB_SITE "https://github.com/your-org/dev-env-installer"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

# Modern UI
!include "MUI2.nsh"
!include "nsDialogs.nsh"
!include "LogicLib.nsh"

# Installer settings
Name "${PRODUCT_NAME}"
OutFile "../DevEnvironmentInstaller.exe"
InstallDir "$PROGRAMFILES64\DevEnvironment"
InstallDirRegKey HKLM "Software\${PRODUCT_NAME}" "InstallPath"
RequestExecutionLevel admin

# Variables for component selection
Var Dialog
Var Label
Var Checkbox_Miniforge
Var Checkbox_Pixi
Var Checkbox_Docker
Var Checkbox_Chrome
Var Checkbox_Franklin
Var Checkbox_Force
Var Checkbox_ContinueOnError

Var Install_Miniforge
Var Install_Pixi
Var Install_Docker
Var Install_Chrome
Var Install_Franklin
Var Force_Install
Var Continue_On_Error

# Interface settings
!define MUI_ABORTWARNING
!define MUI_HEADERIMAGE
!define MUI_WELCOMEFINISHPAGE_BITMAP_NOSTRETCH

# Pages
!insertmacro MUI_PAGE_WELCOME
Page custom ComponentSelectionPage ComponentSelectionPageLeave
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

# Uninstaller pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

# Languages
!insertmacro MUI_LANGUAGE "English"

# Custom page for component selection
Function ComponentSelectionPage
    nsDialogs::Create 1018
    Pop $Dialog

    ${If} $Dialog == error
        Abort
    ${EndIf}

    # Title
    ${NSD_CreateLabel} 0 0 100% 20u "Select Development Tools to Install"
    Pop $Label

    # Components checkboxes
    ${NSD_CreateCheckbox} 20u 30u 200u 12u "Install Miniforge (Python Distribution)"
    Pop $Checkbox_Miniforge
    ${NSD_Check} $Checkbox_Miniforge

    ${NSD_CreateCheckbox} 20u 50u 200u 12u "Install Pixi (Package Manager)"
    Pop $Checkbox_Pixi
    ${NSD_Check} $Checkbox_Pixi

    ${NSD_CreateCheckbox} 20u 70u 200u 12u "Install Docker Desktop"
    Pop $Checkbox_Docker
    ${NSD_Check} $Checkbox_Docker

    ${NSD_CreateCheckbox} 20u 90u 200u 12u "Install Google Chrome"
    Pop $Checkbox_Chrome
    ${NSD_Check} $Checkbox_Chrome

    ${NSD_CreateCheckbox} 20u 110u 200u 12u "Install Franklin (via Pixi)"
    Pop $Checkbox_Franklin
    ${NSD_Check} $Checkbox_Franklin

    # Options
    ${NSD_CreateLabel} 0 140u 100% 12u "Installation Options:"
    Pop $Label

    ${NSD_CreateCheckbox} 20u 160u 200u 12u "Force reinstall if already installed"
    Pop $Checkbox_Force

    ${NSD_CreateCheckbox} 20u 180u 200u 12u "Continue on error (don't stop if one fails)"
    Pop $Checkbox_ContinueOnError

    # Info text
    ${NSD_CreateLabel} 0 210u 100% 40u "This installer will run PowerShell scripts to install the selected development tools. Administrator privileges and internet connection required."
    Pop $Label

    nsDialogs::Show
FunctionEnd

Function ComponentSelectionPageLeave
    ${NSD_GetState} $Checkbox_Miniforge $Install_Miniforge
    ${NSD_GetState} $Checkbox_Pixi $Install_Pixi
    ${NSD_GetState} $Checkbox_Docker $Install_Docker
    ${NSD_GetState} $Checkbox_Chrome $Install_Chrome
    ${NSD_GetState} $Checkbox_Franklin $Install_Franklin
    ${NSD_GetState} $Checkbox_Force $Force_Install
    ${NSD_GetState} $Checkbox_ContinueOnError $Continue_On_Error
FunctionEnd

# Main installation section
Section "MainSection" SEC01
    SetOutPath "$INSTDIR"
    SetOverwrite ifnewer

    # Copy installation scripts
    File "Install-Miniforge.ps1"
    File "Install-Pixi.ps1"
    File "Install-Docker-Desktop.ps1"
    File "Install-Chrome.ps1"
    File "Master-Installer.ps1"

    # Create and run installer batch file
    FileOpen $0 "$INSTDIR\RunInstaller.bat" w
    FileWrite $0 "@echo off$\r$\n"
    FileWrite $0 "cd /d $\"$INSTDIR$\"$\r$\n"
    FileWrite $0 "powershell.exe -ExecutionPolicy Bypass -File $\"$INSTDIR\Master-Installer.ps1$\""
    
    ${If} $Install_Miniforge == 0
        FileWrite $0 " -SkipMiniforge"
    ${EndIf}
    ${If} $Install_Pixi == 0
        FileWrite $0 " -SkipPixi"
    ${EndIf}
    ${If} $Install_Docker == 0
        FileWrite $0 " -SkipDocker"
    ${EndIf}
    ${If} $Install_Chrome == 0
        FileWrite $0 " -SkipChrome"
    ${EndIf}
    ${If} $Install_Franklin == 0
        FileWrite $0 " -SkipFranklin"
    ${EndIf}
    ${If} $Force_Install == 1
        FileWrite $0 " -Force"
    ${EndIf}
    ${If} $Continue_On_Error == 1
        FileWrite $0 " -ContinueOnError"
    ${EndIf}
    
    FileWrite $0 "$\r$\n"
    FileWrite $0 "pause$\r$\n"
    FileClose $0

    # Run the installer
    ExecWait '"$INSTDIR\RunInstaller.bat"' $0
    
    ${If} $0 != 0
        MessageBox MB_ICONEXCLAMATION "Installation completed with some issues."
    ${Else}
        MessageBox MB_ICONINFORMATION "Installation completed successfully!"
    ${EndIf}

    # Create uninstaller
    WriteUninstaller "$INSTDIR\uninst.exe"
    WriteRegStr HKLM "Software\${PRODUCT_NAME}" "InstallPath" "$INSTDIR"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "${PRODUCT_NAME}"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
SectionEnd

# Uninstaller section
Section Uninstall
    RMDir /r "$INSTDIR"
    DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
    DeleteRegKey HKLM "Software\${PRODUCT_NAME}"
SectionEnd

Function .onInit
    StrCpy $Install_Miniforge 1
    StrCpy $Install_Pixi 1
    StrCpy $Install_Docker 1
    StrCpy $Install_Chrome 1
    StrCpy $Install_Franklin 1
    StrCpy $Force_Install 0
    StrCpy $Continue_On_Error 0
FunctionEnd
NSIS_EOF
    
    # Build the installer
    log_info "Compiling NSIS installer..."
    cd "$windows_build_dir"
    if makensis installer.nsi; then
        mv DevEnvironmentInstaller.exe "$DIST_DIR/"
        log_success "Windows installer built: $DIST_DIR/DevEnvironmentInstaller.exe"
    else
        log_error "Failed to build Windows installer"
        return 1
    fi
    
    cd - >/dev/null
}

# Function to build macOS app bundle
build_macos_installer() {
    log_header "Building macOS App Bundle"
    
    local macos_build_dir="$BUILD_DIR/macos"
    local app_name="Development Environment Installer.app"
    local app_bundle="$macos_build_dir/$app_name"
    
    # Create app bundle structure
    log_info "Creating app bundle structure..."
    mkdir -p "$app_bundle/Contents/MacOS"
    mkdir -p "$app_bundle/Contents/Resources"
    
    # Copy bash scripts to Resources
    log_info "Copying bash scripts..."
    cp install-miniforge.sh "$app_bundle/Contents/Resources/"
    cp install-pixi.sh "$app_bundle/Contents/Resources/"
    cp install-docker-desktop.sh "$app_bundle/Contents/Resources/"
    cp install-chrome.sh "$app_bundle/Contents/Resources/"
    cp master-installer.sh "$app_bundle/Contents/Resources/"
    
    # Create Info.plist
    log_info "Creating Info.plist..."
    cat > "$app_bundle/Contents/Info.plist" << 'PLIST_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleDisplayName</key>
    <string>Development Environment Installer</string>
    <key>CFBundleExecutable</key>
    <string>installer</string>
    <key>CFBundleIdentifier</key>
    <string>com.devteam.dev-env-installer</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>Dev Environment Installer</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.14.0</string>
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.developer-tools</string>
    <key>NSAppleScriptEnabled</key>
    <true/>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
PLIST_EOF
    
    # Create main executable script
    log_info "Creating main executable..."
    cat > "$app_bundle/Contents/MacOS/installer" << 'EXEC_EOF'
#!/bin/bash

# Get the app bundle path
APP_BUNDLE="$(cd "$(dirname "$0")/../.." && pwd)"
RESOURCES_DIR="$APP_BUNDLE/Contents/Resources"

# Function to show component selection using AppleScript
show_component_selection() {
    osascript << 'APPLESCRIPT'
    set availableComponents to {"Miniforge (Python Distribution)", "Pixi (Package Manager)", "Docker Desktop", "Google Chrome", "Franklin (via Pixi)"}
    set selectedComponents to choose from list availableComponents with prompt "Select components to install (Cmd+click for multiple):" default items availableComponents with multiple selections allowed with title "Development Environment Installer"
    
    if selectedComponents is false then
        error "Installation cancelled by user."
    end if
    
    set AppleScript's text item delimiters to ","
    return selectedComponents as string
APPLESCRIPT
}

# Function to show options selection
show_options_selection() {
    osascript << 'APPLESCRIPT'
    set optionsResult to display dialog "Installation Options:" & return & return & "Force reinstall: Reinstall components even if already installed" & return & "Continue on error: Don't stop if one component fails" buttons {"Force + Continue", "Force Only", "Continue Only", "Default"} default button "Default" with title "Development Environment Installer"
    return button returned of optionsResult
APPLESCRIPT
}

# Function to confirm installation
confirm_installation() {
    local components="$1"
    local options="$2"
    
    osascript << APPLESCRIPT
    set confirmResult to display dialog "Ready to install!" & return & return & "Components: $components" & return & "Options: $options" & return & return & "Continue?" buttons {"Cancel", "Install"} default button "Install" with title "Development Environment Installer"
    
    if button returned of confirmResult is "Cancel" then
        error "Installation cancelled."
    end if
APPLESCRIPT
}

# Main installation logic
main() {
    # Welcome dialog
    osascript -e 'display dialog "Welcome to the Development Environment Installer!" & return & return & "This will install development tools including Python, package managers, Docker, and more." buttons {"Cancel", "Continue"} default button "Continue" with title "Development Environment Installer"' >/dev/null
    
    if [ $? -ne 0 ]; then
        exit 0
    fi
    
    # Component selection
    local selected_components
    selected_components=$(show_component_selection)
    
    # Options selection
    local selected_options
    selected_options=$(show_options_selection)
    
    # Confirm installation
    confirm_installation "$selected_components" "$selected_options"
    
    # Build command arguments
    local args=""
    
    # Parse component selections
    if [[ ! "$selected_components" == *"Miniforge"* ]]; then
        args="$args --skip-miniforge"
    fi
    if [[ ! "$selected_components" == *"Pixi"* ]]; then
        args="$args --skip-pixi"
    fi
    if [[ ! "$selected_components" == *"Docker"* ]]; then
        args="$args --skip-docker"
    fi
    if [[ ! "$selected_components" == *"Chrome"* ]]; then
        args="$args --skip-chrome"
    fi
    if [[ ! "$selected_components" == *"Franklin"* ]]; then
        args="$args --skip-franklin"
    fi
    
    # Parse options
    case "$selected_options" in
        "Force + Continue")
            args="$args --force --continue-on-error"
            ;;
        "Force Only")
            args="$args --force"
            ;;
        "Continue Only")
            args="$args --continue-on-error"
            ;;
    esac
    
    # Show progress dialog
    osascript -e 'display dialog "Starting installation..." & return & return & "A Terminal window will open to show progress." buttons {"OK"} with title "Development Environment Installer"' >/dev/null
    
    # Run installation in Terminal
    osascript << APPLESCRIPT
    tell application "Terminal"
        activate
        do script "cd '$RESOURCES_DIR' && chmod +x master-installer.sh && ./master-installer.sh$args"
    end tell
APPLESCRIPT
    
    # Show completion dialog
    osascript -e 'display dialog "Installation started!" & return & return & "Check the Terminal window for progress and results." buttons {"OK"} with title "Development Environment Installer"' >/dev/null
}

# Run main function
main
EXEC_EOF
    
    # Make executable
    chmod +x "$app_bundle/Contents/MacOS/installer"
    
    # Copy to dist directory
    cp -R "$app_bundle" "$DIST_DIR/"
    
    log_success "macOS app bundle built: $DIST_DIR/$app_name"
}

# Function to show usage
show_usage() {
    cat << EOF
Cross-Platform Installer Build Script

Usage: $0 [OPTIONS]

Options:
    -h, --help          Show this help message
    -w, --windows-only  Build only Windows installer
    -m, --macos-only    Build only macOS installer
    -c, --clean         Clean build directories before building

Examples:
    $0                  # Build installers for all platforms
    $0 --windows-only   # Build only Windows installer
    $0 --macos-only     # Build only macOS installer
    $0 --clean          # Clean build and rebuild all

Prerequisites:
    - All installer scripts must be in the current directory
    - For Windows: NSIS must be installed and in PATH
    - For macOS: macOS system with osascript support

EOF
}

# Parse command line arguments
parse_arguments() {
    local build_windows=true
    local build_macos=true
    local clean_build=false
    
    while [ $# -gt 0 ]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -w|--windows-only)
                build_windows=true
                build_macos=false
                shift
                ;;
            -m|--macos-only)
                build_windows=false
                build_macos=true
                shift
                ;;
            -c|--clean)
                clean_build=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Clean build directories if requested
    if [ "$clean_build" = true ]; then
        log_info "Cleaning build directories..."
        rm -rf "$BUILD_DIR" "$DIST_DIR"
    fi
    
    # Setup build environment
    setup_build_environment
    
    # Build installers
    local success=true
    
    if [ "$build_windows" = true ]; then
        if ! build_windows_installer; then
            success=false
        fi
    fi
    
    if [ "$build_macos" = true ]; then
        if ! build_macos_installer; then
            success=false
        fi
    fi
    
    # Show summary
    log_header "Build Summary"
    
    if [ "$success" = true ]; then
        log_success "All requested installers built successfully!"
        log_info "Output directory: $DIST_DIR"
        ls -la "$DIST_DIR"
    else
        log_warning "Some installers failed to build. Check the output above for details."
    fi
}

# Main execution
log_header "Cross-Platform Installer Builder"

# Check prerequisites
check_prerequisites

# Parse arguments and build
parse_arguments "$@"