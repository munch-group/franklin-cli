#!/bin/bash

set -euo pipefail

# Early OS check - this script is for macOS only
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "ERROR: This script is for macOS only. Detected OS: $OSTYPE"
    echo "For Linux, please visit: https://docs.docker.com/engine/install/"
    echo "For Windows, please use the PowerShell installer instead."
    exit 1
fi

# Configuration
INSTALL_METHOD="dmg"  # Options: dmg, homebrew
USERNAME=$(whoami)
LOG_FILE="/tmp/docker_install.log"
DOCKER_SETTINGS_DIR="$HOME/Library/Group Containers/group.com.docker"
DOCKER_SETTINGS_FILE="$DOCKER_SETTINGS_DIR/settings-store.json"
BACKUP_DIR="$HOME/.docker/config-backups"

# Command line options
UNINSTALL=false
CLEAN_UNINSTALL=false
STATUS_CHECK=false
CONFIGURE_ONLY=false
FORCE_INSTALL=false
VERBOSE=false
QUIET=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE_INSTALL=true
            shift
            ;;
        --uninstall)
            UNINSTALL=true
            shift
            ;;
        --clean-uninstall)
            CLEAN_UNINSTALL=true
            shift
            ;;
        --status)
            STATUS_CHECK=true
            shift
            ;;
        --configure-only)
            CONFIGURE_ONLY=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --quiet|-quiet)
            QUIET=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --force           Force reinstall (uninstall first if exists)"
            echo "  --uninstall       Remove Docker Desktop (keep user data)"
            echo "  --clean-uninstall Remove Docker Desktop and all data"
            echo "  --status          Show installation status"
            echo "  --configure-only  Only configure existing installation"
            echo "  --verbose         Show detailed logging information"
            echo "  --quiet, -quiet   Show only blue and green colored output"
            echo "  -h, --help        Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

log() {
    if [ "$VERBOSE" = true ]; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
    fi
}

# Conditional echo - suppressed in quiet mode unless colored
echo_unless_quiet() {
    if [ "$QUIET" != true ]; then
        echo "$@"
    fi
}

# Always show green text even in quiet mode
echo_green() {
    echo -e "${GREEN}$@${NC}"
}

# Always show blue text even in quiet mode
echo_blue() {
    echo -e "${BLUE}$@${NC}"
}

# Log errors - suppressed in quiet mode
log_error() {
    if [ "$QUIET" != true ]; then
        echo "$1" | tee -a "$LOG_FILE"
    fi
}

check_requirements() {
    # Check OS type
    if [[ "$OSTYPE" != "darwin"* ]]; then
        log_error "This script is for macOS only. Detected OS: $OSTYPE"
        echo_unless_quiet "For Linux, please visit: https://docs.docker.com/engine/install/"
        echo_unless_quiet "For Windows, please use the PowerShell installer instead."
        exit 1
    fi
    
    # Check macOS version (only if sw_vers is available)
    if command -v sw_vers >/dev/null 2>&1; then
        MACOS_VERSION=$(sw_vers -productVersion)
        MAJOR_VERSION=$(echo $MACOS_VERSION | cut -d. -f1)
        
        if [[ $MAJOR_VERSION -lt 13 ]]; then
            log_error "macOS 13.0 (Ventura) or later required"
            exit 1
        fi
    else
        log "WARNING: Cannot determine macOS version"
    fi
    
    # Check available disk space
    AVAILABLE_SPACE=$(df -g / | tail -1 | awk '{print $4}')
    if [[ $AVAILABLE_SPACE -lt 10 ]]; then
        log_error "Insufficient disk space"
        exit 1
    fi
}

get_installation_status() {
    echo_unless_quiet "=== Docker Desktop Installation Status ==="
    
    # Check if Docker Desktop is installed
    local docker_app="/Applications/Docker.app"
    local docker_installed=false
    
    if [[ -d "$docker_app" ]]; then
        docker_installed=true
        echo_green "[OK] Docker Desktop: Installed"
        
        # Get version info
        local version_plist="$docker_app/Contents/Info.plist"
        if [[ -f "$version_plist" ]]; then
            local version=$(defaults read "$version_plist" CFBundleShortVersionString 2>/dev/null || echo "Unknown")
            echo_unless_quiet "   Version: $version"
        fi
    else
        echo_unless_quiet "[FAILED] Docker Desktop: Not installed"
    fi
    
    # Check if Docker is running
    if pgrep -x "Docker Desktop" > /dev/null; then
        echo_green "[OK] Docker Desktop: Running"
    else
        echo_unless_quiet "[WARNING] Docker Desktop: Not running"
    fi
    
    # Check Docker daemon
    if command -v docker &> /dev/null; then
        if docker info &>/dev/null; then
            echo_green "[OK] Docker Daemon: Running"
        else
            echo_unless_quiet "[WARNING] Docker Daemon: Not accessible"
        fi
    else
        echo_unless_quiet "[FAILED] Docker CLI: Not found"
    fi
    
    # Check privileged helper
    local helper_plist="/Library/LaunchDaemons/com.docker.vmnetd.plist"
    if [[ -f "$helper_plist" ]]; then
        echo_green "[OK] Privileged Helper: Installed"
        if launchctl list | grep -q com.docker.vmnetd; then
            echo_unless_quiet "   Status: Running"
        else
            echo_unless_quiet "   Status: Not running"
        fi
    else
        echo_unless_quiet "[FAILED] Privileged Helper: Not installed"
    fi
    
    # Check configuration files
    echo_unless_quiet ""
    echo_unless_quiet "Configuration Files:"
    if [[ -f "$DOCKER_SETTINGS_FILE" ]]; then
        echo_green "[OK] Settings file: $DOCKER_SETTINGS_FILE"
        local size=$(stat -f%z "$DOCKER_SETTINGS_FILE" 2>/dev/null || echo "0")
        echo_unless_quiet "   Size: $size bytes"
    else
        echo_unless_quiet "[FAILED] Settings file: Not found"
    fi
    
    # Check data usage
    echo_unless_quiet ""
    echo_unless_quiet "Data Usage:"
    local data_paths=(
        "$DOCKER_SETTINGS_DIR"
        "$HOME/.docker"
        "/var/lib/docker"
    )
    
    for path in "${data_paths[@]}"; do
        if [[ -d "$path" ]]; then
            local size=$(du -sh "$path" 2>/dev/null | cut -f1 || echo "Unknown")
            echo_green "[OK] $path: $size"
        else
            echo_unless_quiet "[FAILED] $path: Not found"
        fi
    done
    
    # Check VM disk image
    local vm_disk="$DOCKER_SETTINGS_DIR/Data/vms/0/data/Docker.raw"
    if [[ -f "$vm_disk" ]]; then
        local vm_size=$(du -sh "$vm_disk" 2>/dev/null | cut -f1 || echo "Unknown")
        echo_green "[OK] VM Disk: $vm_size"
    else
        echo_unless_quiet "[FAILED] VM Disk: Not found"
    fi
}

uninstall_docker_desktop() {
    local keep_user_data=${1:-false}
    local silent_mode=${2:-false}
    
    log "Starting Docker Desktop uninstallation..."
    
    # Stop Docker Desktop
    log "Stopping Docker Desktop..."
    osascript -e 'quit app "Docker"' 2>/dev/null || true
    
    # Wait for processes to stop
    local count=0
    while pgrep -x "Docker Desktop" > /dev/null && [[ $count -lt 30 ]]; do
        sleep 1
        ((count++))
    done
    
    # Force kill if still running
    if pgrep -x "Docker Desktop" > /dev/null; then
        log "Force killing Docker Desktop processes..."
        pkill -9 "Docker Desktop" 2>/dev/null || true
        pkill -9 "com.docker" 2>/dev/null || true
    fi
    
    # Remove application
    local docker_app="/Applications/Docker.app"
    if [[ -d "$docker_app" ]]; then
        log "Removing Docker Desktop application..."
        sudo rm -rf "$docker_app"
        echo_green "[OK] Removed: $docker_app"
    fi
    
    # Remove privileged helper
    local helper_plist="/Library/LaunchDaemons/com.docker.vmnetd.plist"
    if [[ -f "$helper_plist" ]]; then
        log "Removing privileged helper..."
        
        # Prompt for password with clear message (unless in silent mode)
        if [[ "$silent_mode" != "true" ]]; then
            echo_unless_quiet
            echo_green "Type your user password and press enter:"
        fi
        sudo -v  # Pre-authenticate sudo to cache credentials
        
        sudo launchctl unload "$helper_plist" 2>/dev/null || true
        sudo rm -f "$helper_plist"
        sudo rm -f "/Library/PrivilegedHelperTools/com.docker.vmnetd"
        echo_green "[OK] Removed privileged helper"
    fi
    
    # Remove symlinks
    local symlinks=(
        "/usr/local/bin/docker"
        "/usr/local/bin/docker-compose"
        "/usr/local/bin/docker-credential-desktop"
        "/usr/local/bin/docker-credential-ecr-login"
        "/usr/local/bin/docker-credential-osxkeychain"
        "/var/run/docker.sock"
    )
    
    for symlink in "${symlinks[@]}"; do
        if [[ -L "$symlink" ]]; then
            sudo rm -f "$symlink"
            echo_green "[OK] Removed symlink: $symlink"
        fi
    done
    
    # Remove user data if requested
    if [[ "$keep_user_data" != "true" ]]; then
        log "Removing user data..."
        
        local user_paths=(
            "$DOCKER_SETTINGS_DIR"
            "$HOME/.docker"
            "$HOME/Library/Containers/com.docker.docker"
            "$HOME/Library/Application Support/Docker Desktop"
            "$HOME/Library/Preferences/com.docker.docker.plist"
            "$HOME/Library/Preferences/com.electron.docker-frontend.plist"
            "$HOME/Library/Saved Application State/com.electron.docker-frontend.savedState"
            "$HOME/Library/Logs/Docker Desktop"
            "$HOME/Library/Caches/com.docker.docker"
        )
        
        for path in "${user_paths[@]}"; do
            if [[ -e "$path" ]]; then
                rm -rf "$path"
                echo_green "[OK] Removed: $path"
            fi
        done
    else
        log "Keeping user data (use --clean-uninstall to remove all data)"
    fi
    
    # Remove system data
    log "Removing system data..."
    local system_paths=(
        "/var/lib/docker"
        "/Library/Logs/Docker Desktop"
        "/tmp/docker.sock"
    )
    
    for path in "${system_paths[@]}"; do
        if [[ -e "$path" ]]; then
            sudo rm -rf "$path" 2>/dev/null || true
            echo_green "[OK] Removed: $path"
        fi
    done
    
    # Clean up processes and kernel extensions
    log "Cleaning up system resources..."
    
    # Remove any remaining Docker processes
    pkill -f "docker" 2>/dev/null || true
    pkill -f "com.docker" 2>/dev/null || true
    
    # Clean up network interfaces (Docker creates these)
    sudo ifconfig bridge0 down 2>/dev/null || true
    
    log "Docker Desktop uninstallation completed!"
    echo_unless_quiet ""
    echo_unless_quiet "Uninstallation Summary:"
    echo_green "[OK] Docker Desktop application removed"
    echo_green "[OK] Privileged helper removed"
    echo_green "[OK] System symlinks removed"
    
    if [[ "$keep_user_data" != "true" ]]; then
        echo_green "[OK] User data removed"
    else
        echo_unless_quiet "[WARNING] User data preserved"
    fi
    
    echo_unless_quiet ""
    echo_blue "You may want to restart your Mac to ensure all resources are cleaned up."
}

install_via_dmg() {
    ARCH=$(uname -m)
    if [[ $ARCH == "arm64" ]]; then
        DOWNLOAD_URL="https://desktop.docker.com/mac/main/arm64/Docker.dmg"
    else
        DOWNLOAD_URL="https://desktop.docker.com/mac/main/amd64/Docker.dmg"
    fi
    
    log "Downloading Docker Desktop for $ARCH"
    if [ "$QUIET" = true ]; then
        curl -L -s -o /tmp/Docker.dmg "$DOWNLOAD_URL"
    else
        curl -L -o /tmp/Docker.dmg "$DOWNLOAD_URL"
    fi
    
    log "Installing Docker Desktop"
    
    # Prompt for password with clear message
    echo_unless_quiet
    echo_green "User Password:"
    sudo -v  # Pre-authenticate sudo to cache credentials
    
    sudo hdiutil attach /tmp/Docker.dmg -nobrowse
    sudo /Volumes/Docker/Docker.app/Contents/MacOS/install \
        --accept-license --user="$USERNAME"
    sudo hdiutil detach /Volumes/Docker
    rm -f /tmp/Docker.dmg
}

configure_docker_desktop() {
    log "Configuring Docker Desktop settings..."
    
    # Ensure Docker Desktop has run at least once
    if [[ ! -f "$DOCKER_SETTINGS_FILE" ]]; then
        log "Launching Docker Desktop for initial setup..."
        open -a Docker
        
        # Wait up to 3 minutes for settings file creation
        local count=0
        while [[ ! -f "$DOCKER_SETTINGS_FILE" ]] && [[ $count -lt 180 ]]; do
            sleep 1
            ((count++))
        done
        
        if [[ ! -f "$DOCKER_SETTINGS_FILE" ]]; then
            log_error "Settings file not created after 3 minutes"
            exit 1
        fi
    fi
    
    # Create backup
    mkdir -p "$BACKUP_DIR"
    cp "$DOCKER_SETTINGS_FILE" "$BACKUP_DIR/settings-$(date +%Y%m%d-%H%M%S).json"
    
    # Check if jq is available
    if ! command -v jq &> /dev/null; then
        log "Installing jq for JSON manipulation..."
        if command -v brew &> /dev/null; then
            brew install jq
        else
            log_error "jq is required but not available. Please install Homebrew or jq manually."
            exit 1
        fi
    fi
    
    # Apply configuration using jq
    local temp_file=$(mktemp)
    
    # Configure Docker Desktop settings to match your requirements
    jq '.memoryMiB = 8000 |
        .cpus = 5 |
        .diskSizeMiB = 25000 |
        .swapMiB = 1024 |
        .autoStart = false |
        .openUIOnStartupDisabled = true |
        .displayedOnboarding = true |
        .enableIntegrityCheck = true |
        .showAnnouncementNotifications = true |
        .showGeneralNotifications = true |
        .useCredentialHelper = true |
        .useResourceSaver = false |
        .autoDownloadUpdates = true |
        .autoPauseTimedActivitySeconds = 30 |
        .autoPauseTimeoutSeconds = 300 |
        .filesharingDirectories = ["/Users", "/Volumes", "/private", "/tmp", "/var/folders"]' \
        "$DOCKER_SETTINGS_FILE" > "$temp_file"
    
    # Apply Apple Silicon optimizations if available
    if [[ $(uname -m) == "arm64" ]]; then
        jq '.useVirtualizationFramework = true |
            .useVirtualizationFrameworkVirtioFS = true |
            .useVirtualizationFrameworkRosetta = true' \
            "$temp_file" > "${temp_file}.arm64" && mv "${temp_file}.arm64" "$temp_file"
    fi
    
    # Validate JSON before replacement
    if jq empty "$temp_file" 2>/dev/null; then
        mv "$temp_file" "$DOCKER_SETTINGS_FILE"
        log "Configuration applied successfully"
        
        # Restart Docker Desktop to apply changes
        log "Stopping Docker Desktop to apply configuration..."
        
        # Force quit Docker Desktop completely (including window)
        osascript -e 'tell application "Docker" to quit' 2>/dev/null || true
        sleep 2
        
        # Kill any remaining Docker processes
        pkill -f "Docker Desktop" 2>/dev/null || true
        pkill -f "com.docker.helper" 2>/dev/null || true
        
        # Wait for Docker to fully stop
        sleep 3
        
        # Start Docker Desktop in background
        log "Starting Docker Desktop to verify configuration..."
        open -a Docker --background
        
        # Wait for Docker daemon to be ready (not the UI)
        local count=0
        local max_attempts=30  # 30 attempts * 2 seconds = 60 seconds max
        
        log "Waiting for Docker daemon to be ready..."
        while [[ $count -lt $max_attempts ]]; do
            if docker info &>/dev/null; then
                log "Docker daemon is ready"
                break
            fi
            sleep 2
            count=$((count + 1))
        done
        
        # Stop Docker Desktop completely after configuration
        log "Stopping Docker Desktop after configuration..."
        
        # First try graceful quit
        osascript -e 'tell application "Docker" to quit' 2>/dev/null || true
        sleep 3
        
        # Force quit if still running
        if pgrep -x "Docker Desktop" > /dev/null; then
            log "Force stopping Docker Desktop..."
            pkill -9 "Docker Desktop" 2>/dev/null || true
        fi
        
        # Kill all Docker-related processes
        pkill -f "com.docker" 2>/dev/null || true
        pkill -f "Docker" 2>/dev/null || true
        
        log "Docker Desktop configuration applied and stopped."
        
    else
        rm "$temp_file"
        log_error "Generated configuration is invalid JSON"
        exit 1
    fi
}

# Main execution logic
main() {
    if [[ "$STATUS_CHECK" == "true" ]]; then
        get_installation_status
        exit 0
    fi
    
    if [[ "$UNINSTALL" == "true" ]] || [[ "$CLEAN_UNINSTALL" == "true" ]]; then
        echo_unless_quiet "Docker Desktop Uninstallation"
        echo_unless_quiet "=============================="
        echo_unless_quiet ""
        
        # Show current status
        get_installation_status
        echo_unless_quiet ""
        
        local keep_data="true"
        if [[ "$CLEAN_UNINSTALL" == "true" ]]; then
            keep_data="false"
            echo_unless_quiet "[WARNING] CLEAN UNINSTALL: This will remove ALL Docker data including:"
            echo_unless_quiet "   - Container images and volumes"
            echo_unless_quiet "   - Docker settings and configuration"
            echo_unless_quiet "   - All user data and preferences"
        else
            echo_blue "Standard uninstall: Docker Desktop will be removed but user data preserved"
        fi
        
        echo_unless_quiet ""
        if [ "$QUIET" = true ]; then
            echo_blue "Proceed with uninstallation? (yes/no): "
            read confirm
        else
            read -p "Proceed with uninstallation? (yes/no): " confirm
        fi
        if [[ "$confirm" != "yes" ]]; then
            echo_unless_quiet "Uninstallation cancelled"
            exit 0
        fi
        
        uninstall_docker_desktop "$keep_data" "false"
        
        echo_unless_quiet ""
        echo_unless_quiet "Final status:"
        get_installation_status
        exit 0
    fi
    
    if [[ "$CONFIGURE_ONLY" == "true" ]]; then
        # Check if Docker Desktop is installed
        if [[ ! -d "/Applications/Docker.app" ]]; then
            log_error "Docker Desktop is not installed. Install it first."
            exit 1
        fi
        configure_docker_desktop
        exit 0
    fi
    
    # Normal installation flow
    log "Starting Docker Desktop installation..."
    check_requirements
    
    # If force flag is set and Docker Desktop exists, uninstall first
    if [[ "$FORCE_INSTALL" == "true" ]] && [[ -d "/Applications/Docker.app" ]]; then
        log "Force flag specified. Uninstalling existing Docker Desktop first..."
        uninstall_docker_desktop "true" "true"  # Keep user data, silent mode for force reinstall
        log "Existing installation removed. Proceeding with fresh installation..."
    fi
    
    install_via_dmg
    configure_docker_desktop
    log "Installation and configuration complete!"
    
    # Stop Docker Desktop completely after installation
    log "Stopping Docker Desktop after installation..."
    
    # First try graceful quit
    osascript -e 'tell application "Docker" to quit' 2>/dev/null || true
    sleep 3
    
    # Force quit if still running
    if pgrep -x "Docker Desktop" > /dev/null; then
        log "Force stopping Docker Desktop..."
        pkill -9 "Docker Desktop" 2>/dev/null || true
    fi
    
    # Kill related processes
    pkill -f "com.docker" 2>/dev/null || true
    pkill -f "Docker" 2>/dev/null || true
    
    # Wait to ensure complete shutdown
    sleep 2
    
    # echo ""
    # echo " Docker Desktop installation completed successfully!"
    # echo ""
    # echo "Docker Desktop has been installed and configured."
    # echo "Docker Desktop has been stopped and is NOT currently running."
    # echo ""
    # echo "Next steps:"
    # echo "1. Start Docker Desktop from Applications when needed"
    # echo "2. Test the installation: docker run hello-world"
    # echo "3. Docker will be available in the menu bar when running"
    # echo ""
    # echo "To uninstall later, run: $0 --uninstall (or --clean-uninstall)"
    # echo "To check status, run: $0 --status"
}

# Run main function
main "$@"
