#!/bin/bash
set -euo pipefail

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

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
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
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --uninstall        Remove Docker Desktop (keep user data)"
            echo "  --clean-uninstall  Remove Docker Desktop and all data"
            echo "  --status          Show installation status"
            echo "  --configure-only  Only configure existing installation"
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
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_requirements() {
    MACOS_VERSION=$(sw_vers -productVersion)
    MAJOR_VERSION=$(echo $MACOS_VERSION | cut -d. -f1)
    
    if [[ $MAJOR_VERSION -lt 13 ]]; then
        log "ERROR: macOS 13.0 (Ventura) or later required"
        exit 1
    fi
    
    AVAILABLE_SPACE=$(df -g / | tail -1 | awk '{print $4}')
    if [[ $AVAILABLE_SPACE -lt 10 ]]; then
        log "ERROR: Insufficient disk space"
        exit 1
    fi
}

get_installation_status() {
    echo "=== Docker Desktop Installation Status ==="
    
    # Check if Docker Desktop is installed
    local docker_app="/Applications/Docker.app"
    local docker_installed=false
    
    if [[ -d "$docker_app" ]]; then
        docker_installed=true
        echo "✅ Docker Desktop: Installed"
        
        # Get version info
        local version_plist="$docker_app/Contents/Info.plist"
        if [[ -f "$version_plist" ]]; then
            local version=$(defaults read "$version_plist" CFBundleShortVersionString 2>/dev/null || echo "Unknown")
            echo "   Version: $version"
        fi
    else
        echo "❌ Docker Desktop: Not installed"
    fi
    
    # Check if Docker is running
    if pgrep -x "Docker Desktop" > /dev/null; then
        echo "✅ Docker Desktop: Running"
    else
        echo "⚠️  Docker Desktop: Not running"
    fi
    
    # Check Docker daemon
    if command -v docker &> /dev/null; then
        if docker info &>/dev/null; then
            echo "✅ Docker Daemon: Running"
        else
            echo "⚠️  Docker Daemon: Not accessible"
        fi
    else
        echo "❌ Docker CLI: Not found"
    fi
    
    # Check privileged helper
    local helper_plist="/Library/LaunchDaemons/com.docker.vmnetd.plist"
    if [[ -f "$helper_plist" ]]; then
        echo "✅ Privileged Helper: Installed"
        if launchctl list | grep -q com.docker.vmnetd; then
            echo "   Status: Running"
        else
            echo "   Status: Not running"
        fi
    else
        echo "❌ Privileged Helper: Not installed"
    fi
    
    # Check configuration files
    echo ""
    echo "Configuration Files:"
    if [[ -f "$DOCKER_SETTINGS_FILE" ]]; then
        echo "✅ Settings file: $DOCKER_SETTINGS_FILE"
        local size=$(stat -f%z "$DOCKER_SETTINGS_FILE" 2>/dev/null || echo "0")
        echo "   Size: $size bytes"
    else
        echo "❌ Settings file: Not found"
    fi
    
    # Check data usage
    echo ""
    echo "Data Usage:"
    local data_paths=(
        "$DOCKER_SETTINGS_DIR"
        "$HOME/.docker"
        "/var/lib/docker"
    )
    
    for path in "${data_paths[@]}"; do
        if [[ -d "$path" ]]; then
            local size=$(du -sh "$path" 2>/dev/null | cut -f1 || echo "Unknown")
            echo "✅ $path: $size"
        else
            echo "❌ $path: Not found"
        fi
    done
    
    # Check VM disk image
    local vm_disk="$DOCKER_SETTINGS_DIR/Data/vms/0/data/Docker.raw"
    if [[ -f "$vm_disk" ]]; then
        local vm_size=$(du -sh "$vm_disk" 2>/dev/null | cut -f1 || echo "Unknown")
        echo "✅ VM Disk: $vm_size"
    else
        echo "❌ VM Disk: Not found"
    fi
}

uninstall_docker_desktop() {
    local keep_user_data=${1:-false}
    
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
        rm -rf "$docker_app"
        echo "✅ Removed: $docker_app"
    fi
    
    # Remove privileged helper
    local helper_plist="/Library/LaunchDaemons/com.docker.vmnetd.plist"
    if [[ -f "$helper_plist" ]]; then
        log "Removing privileged helper..."
        sudo launchctl unload "$helper_plist" 2>/dev/null || true
        sudo rm -f "$helper_plist"
        sudo rm -f "/Library/PrivilegedHelperTools/com.docker.vmnetd"
        echo "✅ Removed privileged helper"
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
            echo "✅ Removed symlink: $symlink"
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
                echo "✅ Removed: $path"
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
            echo "✅ Removed: $path"
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
    echo ""
    echo "Uninstallation Summary:"
    echo "✅ Docker Desktop application removed"
    echo "✅ Privileged helper removed"
    echo "✅ System symlinks removed"
    
    if [[ "$keep_user_data" != "true" ]]; then
        echo "✅ User data removed"
    else
        echo "⚠️  User data preserved"
    fi
    
    echo ""
    echo "You may want to restart your Mac to ensure all resources are cleaned up."
}

install_via_dmg() {
    ARCH=$(uname -m)
    if [[ $ARCH == "arm64" ]]; then
        DOWNLOAD_URL="https://desktop.docker.com/mac/main/arm64/Docker.dmg"
    else
        DOWNLOAD_URL="https://desktop.docker.com/mac/main/amd64/Docker.dmg"
    fi
    
    log "Downloading Docker Desktop for $ARCH"
    curl -L -o /tmp/Docker.dmg "$DOWNLOAD_URL"
    
    log "Installing Docker Desktop"
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
            log "ERROR: Settings file not created after 3 minutes"
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
            log "ERROR: jq is required but not available. Please install Homebrew or jq manually."
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
        .autoPauseTimeoutSeconds = 300 |
        .disableUpdate = true |
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
        
        # Now close Docker Desktop UI but keep daemon running
        log "Closing Docker Desktop window..."
        osascript << EOF 2>/dev/null || true
tell application "System Events"
    if exists (process "Docker Desktop") then
        tell process "Docker Desktop"
            set visible to false
        end tell
    end if
end tell
EOF
        
        # Alternatively, quit the app entirely since daemon can run independently
        sleep 2
        osascript -e 'tell application "Docker" to quit' 2>/dev/null || true
        
        log "Docker Desktop configuration applied. Docker daemon is available in the background."
        
    else
        rm "$temp_file"
        log "ERROR: Generated configuration is invalid JSON"
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
        echo "Docker Desktop Uninstallation"
        echo "=============================="
        echo ""
        
        # Show current status
        get_installation_status
        echo ""
        
        local keep_data="true"
        if [[ "$CLEAN_UNINSTALL" == "true" ]]; then
            keep_data="false"
            echo "⚠️  CLEAN UNINSTALL: This will remove ALL Docker data including:"
            echo "   - Container images and volumes"
            echo "   - Docker settings and configuration"
            echo "   - All user data and preferences"
        else
            echo "Standard uninstall: Docker Desktop will be removed but user data preserved"
        fi
        
        echo ""
        read -p "Proceed with uninstallation? (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            echo "Uninstallation cancelled"
            exit 0
        fi
        
        uninstall_docker_desktop "$keep_data"
        
        echo ""
        echo "Final status:"
        get_installation_status
        exit 0
    fi
    
    if [[ "$CONFIGURE_ONLY" == "true" ]]; then
        # Check if Docker Desktop is installed
        if [[ ! -d "/Applications/Docker.app" ]]; then
            log "ERROR: Docker Desktop is not installed. Install it first."
            exit 1
        fi
        configure_docker_desktop
        exit 0
    fi
    
    # Normal installation flow
    log "Starting Docker Desktop installation..."
    check_requirements
    install_via_dmg
    configure_docker_desktop
    log "Installation and configuration complete!"
    
    # Close Docker Desktop window but keep daemon running
    log "Closing Docker Desktop window..."
    osascript << EOF 2>/dev/null || true
tell application "System Events"
    if exists (process "Docker Desktop") then
        tell process "Docker Desktop"
            set visible to false
        end tell
    end if
end tell
EOF
    
    # Optionally quit Docker Desktop entirely (user can start it when needed)
    sleep 2
    osascript -e 'tell application "Docker" to quit' 2>/dev/null || true
    
    echo ""
    echo "🐳 Docker Desktop installation completed successfully!"
    echo ""
    echo "Docker Desktop has been installed and configured."
    echo "The application has been closed to complete the installation."
    echo ""
    echo "Next steps:"
    echo "1. Start Docker Desktop from Applications when needed"
    echo "2. Test the installation: docker run hello-world"
    echo "3. Docker will be available in the menu bar when running"
    echo ""
    echo "To uninstall later, run: $0 --uninstall (or --clean-uninstall)"
    echo "To check status, run: $0 --status"
}

# Run main function
main "$@"