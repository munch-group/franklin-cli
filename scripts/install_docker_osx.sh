#!/bin/bash
set -e

INSTALL_METHOD="dmg"  # Options: dmg, homebrew
USERNAME=$(whoami)
LOG_FILE="/tmp/docker_install.log"

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

check_requirements
install_via_dmg
log "Installation complete"